from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.session import Base


class Script(Base):
    """剧本。status: uploaded（已上传待解析）| parsed（已解析待校对）
    | reviewed（已校对待结构化）| published（上架可开）| draft（草稿）。"""

    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    player_min: Mapped[int] = mapped_column(Integer, default=4)
    player_max: Mapped[int] = mapped_column(Integer, default=8)
    duration_min: Mapped[int] = mapped_column(Integer, default=180)
    difficulty: Mapped[str] = mapped_column(String(16), default="medium")
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    source_url: Mapped[str] = mapped_column(String(1024), default="")
    source_note: Mapped[str] = mapped_column(String(1024), default="")
    pdf_path: Mapped[str] = mapped_column(String(1024), default="")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    characters: Mapped[list["ScriptCharacter"]] = relationship(
        back_populates="script", cascade="all, delete-orphan"
    )
    clues: Mapped[list["ScriptClue"]] = relationship(
        back_populates="script", cascade="all, delete-orphan"
    )


class ScriptCharacter(Base):
    """剧本角色。个人剧本正文存 description（长文本）；is_murderer 标记真凶。"""

    __tablename__ = "script_characters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("scripts.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    is_murderer: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    script: Mapped["Script"] = relationship(back_populates="characters")


class ScriptClue(Base):
    """线索。clue_type: public（公共）| personal（绑定角色）| hidden（DM 手动投放）。"""

    __tablename__ = "script_clues"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("scripts.id", ondelete="CASCADE"), index=True)
    character_id: Mapped[int | None] = mapped_column(
        ForeignKey("script_characters.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, default="")
    clue_type: Mapped[str] = mapped_column(String(16), default="public")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    script: Mapped["Script"] = relationship(back_populates="clues")
