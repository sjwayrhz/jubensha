from pydantic import BaseModel


class ScriptOut(BaseModel):
    id: int
    title: str
    status: str

    model_config = {"from_attributes": True}
