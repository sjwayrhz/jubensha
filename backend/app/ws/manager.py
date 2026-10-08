"""房间级 WebSocket 连接管理：按 room_id 分组，支持全员/定向推送。"""
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import WebSocket

log = logging.getLogger("jubensha.ws")


def envelope(event_type: str, room_id: int, data: dict) -> dict:
    """统一事件信封：{type, room_id, data, ts}。"""
    return {
        "type": event_type,
        "room_id": room_id,
        "data": data,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


class RoomConnectionManager:
    """room_id -> {user_id: WebSocket}。断线重连由客户端负责。"""

    def __init__(self) -> None:
        self._rooms: dict[int, dict[int, WebSocket]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def _remember_loop(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            self._loop = loop

    async def connect(self, room_id: int, user_id: int, ws: WebSocket) -> None:
        self._remember_loop()
        await ws.accept()
        self._rooms.setdefault(room_id, {})[user_id] = ws
        log.info(
            "WS 连接：room=%d user=%d（当前 %d 人）",
            room_id, user_id, len(self._rooms[room_id]),
        )

    def disconnect(self, room_id: int, user_id: int) -> None:
        group = self._rooms.get(room_id)
        if group and user_id in group:
            del group[user_id]
            log.info("WS 断开：room=%d user=%d", room_id, user_id)
            if not group:
                del self._rooms[room_id]

    async def broadcast(
        self,
        room_id: int,
        event_type: str,
        data: dict,
        user_ids: list[int] | None = None,
    ) -> None:
        """异步广播；user_ids 为 None 则推给房间内所有在线连接。"""
        group = self._rooms.get(room_id, {})
        targets = {
            uid: ws for uid, ws in group.items()
            if user_ids is None or uid in user_ids
        }
        if not targets:
            return
        payload = envelope(event_type, room_id, data)
        dead: list[int] = []
        for uid, ws in targets.items():
            try:
                await ws.send_json(payload)
            except Exception as e:  # noqa: BLE001 — 断线等，发送时清理
                log.warning("WS 发送失败 room=%d user=%d：%s", room_id, uid, e)
                dead.append(uid)
        for uid in dead:
            self.disconnect(room_id, uid)

    def broadcast_sync(
        self,
        room_id: int,
        event_type: str,
        data: dict,
        user_ids: list[int] | None = None,
    ) -> None:
        """供同步（def）接口调用：把广播任务丢到事件循环。无连接时静默跳过。"""
        if not self._rooms.get(room_id):
            return
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self.broadcast(room_id, event_type, data, user_ids), loop
            )
        except RuntimeError as e:
            log.warning("WS 广播调度失败：%s", e)


manager = RoomConnectionManager()
