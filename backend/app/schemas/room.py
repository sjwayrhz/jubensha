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


# ---------- 第三阶段：房间 / DM ----------

class RoomCreateIn(BaseModel):
    script_id: int


class RoomCreateOut(BaseModel):
    id: int
    code: str
    stage: str


class AdvanceIn(BaseModel):
    to: str | None = None  # 不传则走到下一阶段


class AssignIn(BaseModel):
    player_id: int      # 被分配玩家的 user_id
    character_id: int


class ClueRevealIn(BaseModel):
    clue_id: int
    scope: str = "public"          # public | private
    player_id: int | None = None   # scope=private 时必填（user_id）


class VoteIn(BaseModel):
    target_player_id: int  # 被投玩家的 user_id


class RoleUpdateIn(BaseModel):
    role: str  # admin | dm | player


class ScriptBriefOut(BaseModel):
    id: int
    title: str
    description: str = ""
    player_min: int = 4
    player_max: int = 8

    model_config = {"from_attributes": True}


class RoomMemberOut(BaseModel):
    user_id: int
    nickname: str = ""
    character_id: int | None = None
    character_name: str | None = None
    is_ready: bool = False


class RoomDetailOut(BaseModel):
    id: int
    code: str
    stage: str
    current_round: int = 1
    script: ScriptBriefOut | None = None
    players: list[RoomMemberOut] = []


class MyScriptOut(BaseModel):
    character_id: int
    character_name: str
    description: str  # 个人剧本正文


class ClueOut(BaseModel):
    id: int
    title: str
    content: str = ""
    scope: str = "public"


class FinishOut(BaseModel):
    room_id: int
    stage: str
    murderer_name: str | None = None
    murderer_description: str | None = None
    recap: str = ""
