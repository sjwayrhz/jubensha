from pydantic import BaseModel


class RoomOut(BaseModel):
    id: int
    code: str
    stage: str

    model_config = {"from_attributes": True}


class RoomPlayerOut(BaseModel):
    id: int
    user_id: int
    character_id: int | None
    is_ready: bool

    model_config = {"from_attributes": True}
