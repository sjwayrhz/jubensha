"""房间异步语音条：上传 / 列表 / 播放。房间结束后禁言。"""
import logging
import os
import uuid
import wave
from contextlib import closing
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...core.config import settings
from ...core.deps import get_current_user
from ...db.session import get_db
from ...models.chat import VoiceMessage
from ...models.room import Room
from ...models.user import User
from ...ws.manager import manager
from .rooms import _get_room_or_404, _membership_or_403
from ...schemas.chat import VoiceOut

log = logging.getLogger("jubensha.voice")
router = APIRouter(prefix="/rooms", tags=["voice"])

_MEDIA_TYPE = {
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "wav": "audio/wav",
    "amr": "audio/amr",
    "webm": "audio/webm",
}


def _allowed_ext() -> set[str]:
    return {e.strip().lower() for e in settings.voice_allowed_ext.split(",") if e.strip()}


def _wav_duration_sec(path: str) -> float | None:
    try:
        with closing(wave.open(path, "rb")) as f:
            rate = f.getframerate()
            if not rate:
                return None
            return round(f.getnframes() / rate, 1)
    except Exception:  # noqa: BLE001 — 非 wav/损坏文件一律未知时长
        return None


@router.post("/{room_id}/voice", status_code=201)
async def upload_voice(
    room_id: int, file: UploadFile = File(...),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    """上传语音条（mp3/m4a/wav/amr，≤2MB）。成功后 WS 广播 voice_new（仅元信息）。"""
    room = _get_room_or_404(db, room_id)
    _membership_or_403(db, room, user)
    if room.stage == "ended":
        raise HTTPException(400, "房间已结束，禁言")
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if ext not in _allowed_ext():
        raise HTTPException(400, f"不支持的音频格式，仅支持：{sorted(_allowed_ext())}")
    data = await file.read()
    max_bytes = settings.max_voice_mb * 1024 * 1024
    if not data:
        raise HTTPException(400, "空文件")
    if len(data) > max_bytes:
        raise HTTPException(400, f"文件过大（最多 {settings.max_voice_mb}MB）")
    room_dir = os.path.join(settings.voice_dir, str(room.id))
    os.makedirs(room_dir, exist_ok=True)
    fname = f"{uuid.uuid4().hex}.{ext}"
    fpath = os.path.join(room_dir, fname)
    with open(fpath, "wb") as f:
        f.write(data)
    duration = _wav_duration_sec(fpath) if ext == "wav" else None
    vm = VoiceMessage(
        room_id=room.id, sender_id=user.id,
        file_path=fpath, duration_sec=duration,
    )
    db.add(vm)
    db.commit()
    db.refresh(vm)
    manager.broadcast_sync(room.id, "voice_new", {
        "id": vm.id,
        "sender_id": user.id,
        "sender_nickname": user.nickname or "",
        "duration_sec": vm.duration_sec,
        "created_at": vm.created_at.isoformat() if isinstance(vm.created_at, datetime) else str(vm.created_at),
    })
    log.info("语音条：room=%d user=%d voice=%d ext=%s", room.id, user.id, vm.id, ext)
    return {
        "id": vm.id, "room_id": room.id, "sender_id": user.id,
        "sender_nickname": user.nickname or "", "duration_sec": vm.duration_sec,
        "created_at": vm.created_at.isoformat() if isinstance(vm.created_at, datetime) else str(vm.created_at),
    }


@router.get("/{room_id}/voice", response_model=list[VoiceOut])
def list_voice(
    room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """语音条元信息列表（不含文件内容）。"""
    room = _get_room_or_404(db, room_id)
    _membership_or_403(db, room, user)
    rows = (
        db.query(VoiceMessage, User.nickname)
        .join(User, VoiceMessage.sender_id == User.id)
        .filter(VoiceMessage.room_id == room.id)
        .order_by(VoiceMessage.id)
        .all()
    )
    return [
        VoiceOut(
            id=v.id, room_id=v.room_id, sender_id=v.sender_id,
            sender_nickname=nickname or "", duration_sec=v.duration_sec,
            created_at=v.created_at,
        )
        for v, nickname in rows
    ]


@router.get("/{room_id}/voice/{voice_id}/play")
def play_voice(
    room_id: int, voice_id: int,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    """播放语音条：仅房间成员可下载。"""
    room = _get_room_or_404(db, room_id)
    _membership_or_403(db, room, user)
    vm = db.get(VoiceMessage, voice_id)
    if not vm or vm.room_id != room.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "语音条不存在")
    if not os.path.isfile(vm.file_path):
        raise HTTPException(404, "音频文件丢失")
    ext = vm.file_path.rsplit(".", 1)[-1].lower()
    return FileResponse(
        vm.file_path,
        media_type=_MEDIA_TYPE.get(ext, "application/octet-stream"),
        filename=f"voice_{vm.id}.{ext}",
    )
