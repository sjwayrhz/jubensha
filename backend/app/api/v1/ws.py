"""WebSocket：房间实时事件推送。鉴权走 query 参数 ?token=（JWT）。"""
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ...core.security import decode_token
from ...db.session import SessionLocal
from ...models.room import Room, RoomPlayer
from ...models.user import User
from ...ws.manager import manager

log = logging.getLogger("jubensha.ws")
router = APIRouter()


def _auth_user(db: Session, token: str) -> User | None:
    try:
        payload = decode_token(token or "")
        user = db.get(User, int(payload.get("sub", 0)))
    except Exception:  # noqa: BLE001 — token 非法一律视为未认证
        return None
    return user


@router.websocket("/ws/rooms/{room_id}")
async def room_ws(
    websocket: WebSocket, room_id: int, token: str = Query(default="")
):
    """房间事件通道。非成员/非法 token 直接关闭连接（4401/4403/4404）。"""
    db = SessionLocal()
    try:
        user = _auth_user(db, token)
        if not user:
            await websocket.accept()
            await websocket.close(code=4401)
            return
        room = db.get(Room, room_id)
        if not room:
            await websocket.accept()
            await websocket.close(code=4404)
            return
        is_member = (
            user.role == "admin"
            or room.dm_id == user.id
            or db.query(RoomPlayer)
            .filter_by(room_id=room.id, user_id=user.id)
            .first()
            is not None
        )
        if not is_member:
            await websocket.accept()
            await websocket.close(code=4403)
            return
        await manager.connect(room_id, user.id, websocket)
        try:
            while True:
                # 客户端心跳/消息原样忽略；断开由异常感知
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            manager.disconnect(room_id, user.id)
    finally:
        db.close()
