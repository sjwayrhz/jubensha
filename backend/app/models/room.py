from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.session import Base

# 开本流水阶段（服务端强制校验，非法流转直接 400）
STAGE_FLOW = [
    "waiting",       # 等待玩家加入
    "selecting",     # 选角
    "reading",       # 个人读本
    "investigating", # 搜证
    "discussing",    # 讨论
    "voting",        # 投票
    "reveal",        # 真相复盘
    "ended",         # 结束
]
TRANSITIONS: dict[str, list[str]] = {
    s: [STAGE_FLOW[i + 1]] for i, s in enumerate(STAGE_FLOW[:-1])
}
TRANSITIONS["ended"] = []


class Room(Base):
    """房间。stage 取值见 STAGE_FLOW。"""

    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("scripts.id"))
    dm_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    stage: Mapped[str] = mapped_column(String(16), default="waiting", index=True)
    current_round: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    players: Mapped[list["RoomPlayer"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )


class RoomPlayer(Base):
    """房间成员：用户 ↔ 角色绑定。"""

    __tablename__ = "room_players"
    __table_args__ = (UniqueConstraint("room_id", "user_id", name="uq_room_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    character_id: Mapped[int | None] = mapped_column(
        ForeignKey("script_characters.id", ondelete="SET NULL"), nullable=True
    )
    is_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    room: Mapped["Room"] = relationship(back_populates="players")


class RoomClue(Base):
    """房间内已投放的线索。visible_scope: public（全体可见）| private（仅 player_id 可见）。"""

    __tablename__ = "room_clues"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    clue_id: Mapped[int] = mapped_column(ForeignKey("script_clues.id", ondelete="CASCADE"))
    visible_scope: Mapped[str] = mapped_column(String(16), default="public")
    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    revealed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Vote(Base):
    """投票：一房一人一票（uq_room_voter 约束）。voter/target 均为 users.id。"""

    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("room_id", "voter_id", name="uq_room_voter"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    voter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    target_player_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
