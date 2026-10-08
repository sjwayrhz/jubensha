"""房间文字聊天：发送 / 拉取。房间结束后禁言。"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...core.deps import get_current_user
from ...db.session import get_db
from ...models.chat import ChatMessage
from ...models.room import Room
from ...models.user import User
from ...ws.manager import manager
from .rooms import _get_room_or_404, _membership_or_403
from ...schemas.chat import ChatIn, ChatOut

log = logging.getLogger("jubensha.chat")
router = APIRouter(prefix="/rooms", tags=["chat"])

MAX_CONTENT_LEN = 2000


@router.post("/{room_id}/chat", status_code=201)
def send_chat(
    room_id: int, data: ChatIn,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    """房间成员发送文字消息；房间结束后禁言。成功后 WS 广播 chat_new。"""
    room = _get_room_or_404(db, room_id)
    _membership_or_403(db, room, user)
    if room.stage == "ended":
        raise HTTPException(400, "房间已结束，禁言")
    content = (data.content or "").strip()
    if not content:
        raise HTTPException(400, "消息内容不能为空")
    if len(content) > MAX_CONTENT_LEN:
        raise HTTPException(400, f"消息过长（最多 {MAX_CONTENT_LEN} 字）")
    msg = ChatMessage(room_id=room.id, sender_id=user.id, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    manager.broadcast_sync(room.id, "chat_new", {
        "id": msg.id,
        "sender_id": user.id,
        "sender_nickname": user.nickname or "",
        "content": msg.content,
        "created_at": msg.created_at.isoformat() if isinstance(msg.created_at, datetime) else str(msg.created_at),
    })
    log.info("聊天：room=%d user=%d msg=%d", room.id, user.id, msg.id)
    return {
        "id": msg.id, "room_id": room.id, "sender_id": user.id,
        "sender_nickname": user.nickname or "", "content": msg.content,
        "created_at": msg.created_at.isoformat() if isinstance(msg.created_at, datetime) else str(msg.created_at),
    }


@router.get("/{room_id}/chat", response_model=list[ChatOut])
def list_chat(
    room_id: int, since: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    """拉取聊天记录；since 传消息 id，只返回更新的（增量同步用）。"""
    room = _get_room_or_404(db, room_id)
    _membership_or_403(db, room, user)
    rows = (
        db.query(ChatMessage, User.nickname)
        .join(User, ChatMessage.sender_id == User.id)
        .filter(ChatMessage.room_id == room.id, ChatMessage.id > since)
        .order_by(ChatMessage.id)
        .limit(limit)
        .all()
    )
    return [
        ChatOut(
            id=m.id, room_id=m.room_id, sender_id=m.sender_id,
            sender_nickname=nickname or "", content=m.content,
            created_at=m.created_at,
        )
        for m, nickname in rows
    ]
