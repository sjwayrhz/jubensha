from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)  # bcrypt 上限 72 字节
    nickname: str = Field(default="", max_length=64)


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    nickname: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
