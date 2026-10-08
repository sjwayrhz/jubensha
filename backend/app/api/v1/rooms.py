"""玩家端房间 API：加入房间、查看状态/个人剧本/线索、投票。"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...core.deps import get_current_user
from ...db.session import get_db
from ...models.room import Room, RoomClue, RoomPlayer, Vote
from ...models.script import Script, ScriptCharacter, ScriptClue
from ...models.user import User
from ...ws.manager import manager
from ...schemas.room import (
    CharacterBriefOut,
    ClueOut,
    FinishOut,
    HandIn,
    MyScriptOut,
    RoomDetailOut,
    RoomMemberOut,
    RoomOut,
    ScriptBriefOut,
    SelectCharacterIn,
    VoteIn,
)

log = logging.getLogger("jubensha.rooms")
router = APIRouter(prefix="/rooms", tags=["rooms"])

# 个人剧本可见的起始阶段
SCRIPT_VISIBLE_FROM = {"reading", "investigating", "discussing", "voting", "reveal", "ended"}


def _get_room_or_404(db: Session, room_id: int) -> Room:
    room = db.get(Room, room_id)
    if not room:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "房间不存在")
    return room


def _membership_or_403(db: Session, room: Room, user: User) -> RoomPlayer:
    """玩家本人 / 本房 DM / admin 可见；返回玩家本人的成员记录（DM/admin 可能为 None）。"""
    if user.role == "admin" or room.dm_id == user.id:
        return db.query(RoomPlayer).filter_by(room_id=room.id, user_id=user.id).first()
    member = db.query(RoomPlayer).filter_by(room_id=room.id, user_id=user.id).first()
    if not member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "你不在这个房间")
    return member


def _room_detail(db: Session, room: Room) -> RoomDetailOut:
    script = db.get(Script, room.script_id)
    chars = {
        c.id: c.name
        for c in db.query(ScriptCharacter).filter_by(script_id=room.script_id).all()
    }
    members = (
        db.query(RoomPlayer, User)
        .join(User, RoomPlayer.user_id == User.id)
        .filter(RoomPlayer.room_id == room.id)
        .all()
    )
    return RoomDetailOut(
        id=room.id, code=room.code, stage=room.stage, current_round=room.current_round,
        script=ScriptBriefOut.model_validate(script) if script else None,
        players=[
            RoomMemberOut(
                user_id=u.id, nickname=u.nickname,
                character_id=rp.character_id,
                character_name=chars.get(rp.character_id),
                is_ready=rp.is_ready,
            )
            for rp, u in members
        ],
    )


@router.post("/join", response_model=RoomOut)
def join_room(code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """凭 6 位房间码加入房间（waiting/selecting 阶段可进，已加入则幂等返回）。"""
    room = db.query(Room).filter_by(code=code.strip().upper()).first()
    if not room:
        raise HTTPException(404, "房间码无效")
    if room.stage not in ("waiting", "selecting"):
        raise HTTPException(400, f"房间已开局（{room.stage}），不能加入")
    member = db.query(RoomPlayer).filter_by(room_id=room.id, user_id=user.id).first()
    if not member:
        member = RoomPlayer(room_id=room.id, user_id=user.id)
        db.add(member)
        db.commit()
        log.info("加入房间：room=%d user=%d", room.id, user.id)
        manager.broadcast_sync(room.id, "player_joined", {
            "user_id": user.id,
            "nickname": user.nickname or "",
        })
    return RoomOut.model_validate(room)


@router.get("/{room_id}", response_model=RoomDetailOut)
def get_room(room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """按当前阶段返回房间可见状态（不含他人个人剧本）。"""
    room = _get_room_or_404(db, room_id)
    _membership_or_403(db, room, user)
    return _room_detail(db, room)


@router.get("/{room_id}/my-script", response_model=MyScriptOut)
def get_my_script(
    room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """只返回自己的角色剧本；读本阶段后可见。"""
    room = _get_room_or_404(db, room_id)
    member = db.query(RoomPlayer).filter_by(room_id=room.id, user_id=user.id).first()
    if not member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "你不在这个房间")
    if room.stage not in SCRIPT_VISIBLE_FROM:
        raise HTTPException(400, f"当前阶段 {room.stage}，个人剧本尚未发放")
    if not member.character_id:
        raise HTTPException(400, "DM 尚未给你分配角色")
    char = db.get(ScriptCharacter, member.character_id)
    if not char:
        raise HTTPException(404, "角色不存在")
    return MyScriptOut(
        character_id=char.id, character_name=char.name, description=char.description or ""
    )


@router.get("/{room_id}/clues", response_model=list[ClueOut])
def get_my_clues(
    room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """只返回对自己可见的线索：公开的 + 定向给自己的。"""
    room = _get_room_or_404(db, room_id)
    _membership_or_403(db, room, user)
    rows = (
        db.query(RoomClue, ScriptClue)
        .join(ScriptClue, RoomClue.clue_id == ScriptClue.id)
        .filter(RoomClue.room_id == room.id)
        .filter(
            (RoomClue.visible_scope == "public")
            | ((RoomClue.visible_scope == "private") & (RoomClue.player_id == user.id))
        )
        .order_by(RoomClue.revealed_at)
        .all()
    )
    return [
        ClueOut(id=c.id, title=c.title, content=c.content or "", scope=rc.visible_scope)
        for rc, c in rows
    ]


@router.get("/{room_id}/characters", response_model=list[CharacterBriefOut])
def get_room_characters(
    room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """本房剧本的人物名单（不含真凶标记，供单人本投票指认用）。"""
    room = _get_room_or_404(db, room_id)
    _membership_or_403(db, room, user)
    return (
        db.query(ScriptCharacter)
        .filter_by(script_id=room.script_id)
        .order_by(ScriptCharacter.sort_order, ScriptCharacter.id)
        .all()
    )


@router.get("/{room_id}/result", response_model=FinishOut)
def get_result(
    room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """公布真相后，房间成员查看真凶与复盘。"""
    room = _get_room_or_404(db, room_id)
    _membership_or_403(db, room, user)
    if room.stage not in ("reveal", "ended"):
        raise HTTPException(400, f"当前阶段 {room.stage}，真相尚未公布")
    murderer = (
        db.query(ScriptCharacter)
        .filter_by(script_id=room.script_id, is_murderer=True)
        .first()
    )
    script = db.get(Script, room.script_id)
    my_accused_name = None
    my_vote = (
        db.query(Vote)
        .filter_by(room_id=room.id, voter_id=user.id)
        .filter(Vote.target_character_id.isnot(None))
        .first()
    )
    if my_vote:
        accused = db.get(ScriptCharacter, my_vote.target_character_id)
        my_accused_name = accused.name if accused else None
    return FinishOut(
        room_id=room.id, stage=room.stage,
        murderer_name=murderer.name if murderer else None,
        murderer_description=murderer.description if murderer else None,
        recap=script.description if script else "",
        my_accused_name=my_accused_name,
    )


@router.post("/{room_id}/select-character")
def select_character(
    room_id: int, data: SelectCharacterIn, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """选角阶段玩家自选角色：只能在 selecting 阶段；角色不能被别人已选；可改选。"""
    room = _get_room_or_404(db, room_id)
    member = db.query(RoomPlayer).filter_by(room_id=room.id, user_id=user.id).first()
    if not member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "你不在这个房间")
    if room.stage != "selecting":
        raise HTTPException(400, f"当前阶段 {room.stage}，不能选角")
    char = db.get(ScriptCharacter, data.character_id)
    if not char or char.script_id != room.script_id:
        raise HTTPException(400, "角色不属于本房剧本")
    taken = (
        db.query(RoomPlayer)
        .filter(
            RoomPlayer.room_id == room.id,
            RoomPlayer.character_id == char.id,
            RoomPlayer.user_id != user.id,
        )
        .first()
    )
    if taken:
        raise HTTPException(400, "该角色已被其他玩家选择")
    member.character_id = char.id
    db.commit()
    log.info("选角：room=%d user=%d char=%s", room.id, user.id, char.name)
    manager.broadcast_sync(room.id, "character_selected", {
        "user_id": user.id, "character_id": char.id, "character_name": char.name,
    })
    return {"room_id": room.id, "user_id": user.id,
            "character_id": char.id, "character_name": char.name}


@router.post("/{room_id}/hand")
def raise_hand(
    room_id: int, data: HandIn, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """读本/讨论阶段玩家举手（表示已读完/发言完毕），可放下。"""
    room = _get_room_or_404(db, room_id)
    member = db.query(RoomPlayer).filter_by(room_id=room.id, user_id=user.id).first()
    if not member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "你不在这个房间")
    if room.stage not in ("reading", "discussing"):
        raise HTTPException(400, f"当前阶段 {room.stage}，不能举手")
    member.is_ready = data.raised
    db.commit()
    manager.broadcast_sync(room.id, "hand_update", {
        "user_id": user.id, "hand_raised": data.raised,
    })
    return {"room_id": room.id, "user_id": user.id, "hand_raised": data.raised}


@router.post("/{room_id}/vote")
def cast_vote(
    room_id: int, data: VoteIn, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """投票阶段内一人一票。
    多人本：target_player_id 投玩家，不能投自己，目标必须是房内玩家。
    单人本：target_character_id 指认人物（可含 NPC），人物必须属于本房剧本。
    两者二选一。"""
    room = _get_room_or_404(db, room_id)
    member = db.query(RoomPlayer).filter_by(room_id=room.id, user_id=user.id).first()
    if not member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "你不在这个房间")
    if room.stage != "voting":
        raise HTTPException(400, f"当前阶段 {room.stage}，不在投票中")
    if bool(data.target_player_id) == bool(data.target_character_id):
        raise HTTPException(400, "请指定投票目标：玩家或人物二选一")
    target_character_id = None
    if data.target_player_id:
        if data.target_player_id == user.id:
            raise HTTPException(400, "不能投自己")
        target = (
            db.query(RoomPlayer)
            .filter_by(room_id=room.id, user_id=data.target_player_id)
            .first()
        )
        if not target:
            raise HTTPException(400, "投票目标不在房间内")
    else:
        char = (
            db.query(ScriptCharacter)
            .filter_by(id=data.target_character_id, script_id=room.script_id)
            .first()
        )
        if not char:
            raise HTTPException(400, "指认的人物不属于本房剧本")
        target_character_id = char.id
    existed = (
        db.query(Vote).filter_by(room_id=room.id, voter_id=user.id).first()
    )
    if existed:
        raise HTTPException(400, "你已经投过票了，一人一票")
    db.add(Vote(
        room_id=room.id, voter_id=user.id,
        target_player_id=data.target_player_id,
        target_character_id=target_character_id,
    ))
    db.commit()
    log.info("投票：room=%d voter=%d target_player=%s target_char=%s",
             room.id, user.id, data.target_player_id, target_character_id)
    manager.broadcast_sync(room.id, "vote_update", _vote_counts(db, room.id))
    return {"room_id": room.id, "voter_id": user.id,
            "target_player_id": data.target_player_id,
            "target_character_id": target_character_id}


def _vote_counts(db: Session, room_id: int) -> dict:
    """投票计数（开票前只给计数，不透露谁投谁）。
    投玩家的计数 key 为 str(user_id)，指认人物的 key 为 f"c{character_id}"。"""
    counts: dict[str, int] = {}
    for target, n in (
        db.query(Vote.target_player_id, func.count(Vote.id))
        .filter(Vote.room_id == room_id, Vote.target_player_id.isnot(None))
        .group_by(Vote.target_player_id)
        .all()
    ):
        counts[str(target)] = n
    for cid, n in (
        db.query(Vote.target_character_id, func.count(Vote.id))
        .filter(Vote.room_id == room_id, Vote.target_character_id.isnot(None))
        .group_by(Vote.target_character_id)
        .all()
    ):
        counts[f"c{cid}"] = n
    return {"counts": counts, "total": sum(counts.values())}
