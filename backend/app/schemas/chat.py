"""聊天 / 语音条 schemas。"""
from datetime import datetime

from pydantic import BaseModel


class ChatIn(BaseModel):
    content: str


class ChatOut(BaseModel):
    id: int
    room_id: int
    sender_id: int
    sender_nickname: str = ""
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class VoiceOut(BaseModel):
    id: int
    room_id: int
    sender_id: int
    sender_nickname: str = ""
    duration_sec: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
