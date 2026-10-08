"""DM 控场 API：建房、切阶段、分配角色、投放线索、投票开关、公布真相。"""
import logging
import random

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.deps import require_dm
from ...db.session import get_db
from ...models.room import TRANSITIONS, Room, RoomClue, RoomPlayer
from ...models.script import Script, ScriptCharacter, ScriptClue
from ...models.user import User
from ...ws.manager import manager
from ...schemas.room import (
    AdvanceIn,
    AssignIn,
    ClueRevealIn,
    FinishOut,
    RoomCreateIn,
    RoomCreateOut,
)

log = logging.getLogger("jubensha.dm")
router = APIRouter(prefix="/dm", tags=["dm"])

_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def _gen_code(db: Session) -> str:
    for _ in range(20):
        code = "".join(random.choice(_CODE_ALPHABET) for _ in range(6))
        if not db.query(Room).filter_by(code=code).first():
            return code
    raise HTTPException(500, "房间码生成失败，请重试")


def _get_room_or_404(db: Session, room_id: int) -> Room:
    room = db.get(Room, room_id)
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "房间不存在")
    return room


def _require_room_dm(room: Room, dm: User) -> None:
    if dm.role != "admin" and room.dm_id != dm.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "不是本房 DM")


def _transition(db: Session, room: Room, to: str) -> Room:
    allowed = TRANSITIONS.get(room.stage, [])
    if to not in allowed:
        raise HTTPException(
            400, f"非法流转：{room.stage} → {to}（允许：{allowed or '无'}）"
        )
    room.stage = to
    db.commit()
    db.refresh(room)
    log.info("房间切阶段：room=%d %s", room.id, to)
    return room


@router.post("/rooms", response_model=RoomCreateOut, status_code=201)
def create_room(data: RoomCreateIn, db: Session = Depends(get_db), dm: User = Depends(require_dm)):
    """DM 选已发布剧本建房，返回 6 位房间码。"""
    script = db.get(Script, data.script_id)
    if not script:
        raise HTTPException(404, "剧本不存在")
    if script.status != "published":
        raise HTTPException(400, "剧本未发布，不能开房")
    room = Room(code=_gen_code(db), script_id=script.id, dm_id=dm.id, stage="waiting")
    db.add(room)
    db.commit()
    db.refresh(room)
    log.info("建房：room=%d code=%s script=%d dm=%d", room.id, room.code, script.id, dm.id)
    return RoomCreateOut(id=room.id, code=room.code, stage=room.stage)


@router.post("/rooms/{room_id}/start")
def start_room(room_id: int, db: Session = Depends(get_db), dm: User = Depends(require_dm)):
    """开局：waiting → selecting。"""
    room = _get_room_or_404(db, room_id)
    _require_room_dm(room, dm)
    if room.stage != "waiting":
        raise HTTPException(400, f"当前阶段 {room.stage}，不能开局")
    room = _transition(db, room, "selecting")
    manager.broadcast_sync(room.id, "stage_changed", {"stage": room.stage})
    return {"room_id": room.id, "stage": room.stage}


@router.post("/rooms/{room_id}/assign")
def assign_character(
    room_id: int, data: AssignIn, db: Session = Depends(get_db), dm: User = Depends(require_dm)
):
    """DM 分配角色：player_id（user_id）↔ character_id。限 selecting/reading 阶段。"""
    room = _get_room_or_404(db, room_id)
    _require_room_dm(room, dm)
    if room.stage not in ("selecting", "reading"):
        raise HTTPException(400, f"当前阶段 {room.stage}，不能分配角色")
    member = (
        db.query(RoomPlayer)
        .filter_by(room_id=room.id, user_id=data.player_id)
        .first()
    )
    if not member:
        raise HTTPException(400, "该玩家不在房间内")
    char = db.get(ScriptCharacter, data.character_id)
    if not char or char.script_id != room.script_id:
        raise HTTPException(400, "角色不属于本房剧本")
    taken = (
        db.query(RoomPlayer)
        .filter(
            RoomPlayer.room_id == room.id,
            RoomPlayer.character_id == char.id,
            RoomPlayer.user_id != data.player_id,
        )
        .first()
    )
    if taken:
        raise HTTPException(400, "该角色已被其他玩家占用")
    member.character_id = char.id
    db.commit()
    log.info("分配角色：room=%d user=%d char=%s", room.id, data.player_id, char.name)
    return {"room_id": room.id, "player_id": data.player_id, "character_id": char.id,
            "character_name": char.name}


@router.post("/rooms/{room_id}/advance")
def advance_stage(
    room_id: int, data: AdvanceIn, db: Session = Depends(get_db), dm: User = Depends(require_dm)
):
    """按合法流转切阶段；to 不传则走下一步。非法流转 400。"""
    room = _get_room_or_404(db, room_id)
    _require_room_dm(room, dm)
    to = data.to
    if to is None:
        allowed = TRANSITIONS.get(room.stage, [])
        if len(allowed) != 1:
            raise HTTPException(400, f"当前阶段 {room.stage} 需要明确指定 to")
        to = allowed[0]
    room = _transition(db, room, to)
    manager.broadcast_sync(room.id, "stage_changed", {"stage": room.stage})
    return {"room_id": room.id, "stage": room.stage}


@router.post("/rooms/{room_id}/clues/reveal", status_code=201)
def reveal_clue(
    room_id: int, data: ClueRevealIn, db: Session = Depends(get_db), dm: User = Depends(require_dm)
):
    """投放线索：公开（全体）或定向某玩家。"""
    room = _get_room_or_404(db, room_id)
    _require_room_dm(room, dm)
    if data.scope not in ("public", "private"):
        raise HTTPException(400, "scope 只能是 public 或 private")
    clue = db.get(ScriptClue, data.clue_id)
    if not clue or clue.script_id != room.script_id:
        raise HTTPException(400, "线索不属于本房剧本")
    if data.scope == "private":
        if not data.player_id:
            raise HTTPException(400, "定向线索必须指定 player_id")
        member = (
            db.query(RoomPlayer)
            .filter_by(room_id=room.id, user_id=data.player_id)
            .first()
        )
        if not member:
            raise HTTPException(400, "目标玩家不在房间内")
    rc = RoomClue(
        room_id=room.id, clue_id=clue.id,
        visible_scope=data.scope, player_id=data.player_id,
    )
    db.add(rc)
    db.commit()
    db.refresh(rc)
    log.info("投放线索：room=%d clue=%d scope=%s", room.id, clue.id, data.scope)
    clue_data = {
        "room_clue_id": rc.id,
        "clue_id": clue.id,
        "title": clue.title,
        "content": clue.content or "",
        "scope": rc.visible_scope,
    }
    if rc.visible_scope == "public":
        manager.broadcast_sync(room.id, "clue_revealed", clue_data)
    else:
        # 定向线索只推给目标玩家
        manager.broadcast_sync(room.id, "clue_revealed", clue_data, user_ids=[data.player_id])
    return {"room_clue_id": rc.id, "scope": rc.visible_scope}


@router.post("/rooms/{room_id}/vote/open")
def open_vote(room_id: int, db: Session = Depends(get_db), dm: User = Depends(require_dm)):
    """开启投票：discussing → voting（已在 voting 则幂等返回）。"""
    room = _get_room_or_404(db, room_id)
    _require_room_dm(room, dm)
    if room.stage == "voting":
        return {"room_id": room.id, "stage": room.stage}
    room = _transition(db, room, "voting")
    manager.broadcast_sync(room.id, "vote_opened", {"stage": room.stage})
    return {"room_id": room.id, "stage": room.stage}


@router.post("/rooms/{room_id}/vote/close")
def close_vote(room_id: int, db: Session = Depends(get_db), dm: User = Depends(require_dm)):
    """关闭投票：voting → reveal。"""
    room = _get_room_or_404(db, room_id)
    _require_room_dm(room, dm)
    room = _transition(db, room, "reveal")
    manager.broadcast_sync(room.id, "vote_closed", {"stage": room.stage})
    return {"room_id": room.id, "stage": room.stage}


@router.post("/rooms/{room_id}/finish", response_model=FinishOut)
def finish_room(room_id: int, db: Session = Depends(get_db), dm: User = Depends(require_dm)):
    """公布真相：reveal → ended，返回真凶与复盘文本。"""
    room = _get_room_or_404(db, room_id)
    _require_room_dm(room, dm)
    if room.stage != "reveal":
        raise HTTPException(400, f"当前阶段 {room.stage}，不能公布真相")
    murderer = (
        db.query(ScriptCharacter)
        .filter_by(script_id=room.script_id, is_murderer=True)
        .first()
    )
    if not murderer:
        raise HTTPException(400, "剧本未标记真凶，无法公布")
    script = db.get(Script, room.script_id)
    room = _transition(db, room, "ended")
    manager.broadcast_sync(room.id, "room_ended", {
        "stage": room.stage,
        "murderer_name": murderer.name,
    })
    return FinishOut(
        room_id=room.id, stage=room.stage,
        murderer_name=murderer.name, murderer_description=murderer.description,
        recap=script.description if script else "",
    )
