from pydantic import BaseModel


class ScriptOut(BaseModel):
    id: int
    title: str
    status: str

    model_config = {"from_attributes": True}


class ScriptPublicOut(BaseModel):
    """玩家端剧本列表：只含已发布的公开信息。"""

    id: int
    title: str
    description: str
    player_min: int
    player_max: int

    model_config = {"from_attributes": True}


class ScriptUploadOut(BaseModel):
    script_id: int
    status: str


class ScriptParseOut(BaseModel):
    script_id: int
    status: str
    method: str
    chars: int


class ScriptRawOut(BaseModel):
    script_id: int
    title: str
    status: str
    raw_text: str


class ScriptRawIn(BaseModel):
    raw_text: str


class ScriptStructureOut(BaseModel):
    script_id: int
    status: str
    characters: int
    clues: int
