"""玩家端剧本接口：只读已发布的剧本。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.deps import get_current_user
from ...db.session import get_db
from ...models.script import Script
from ...models.user import User
from ...schemas.script import ScriptPublicOut

router = APIRouter(prefix="/scripts", tags=["scripts"])


@router.get("", response_model=list[ScriptPublicOut])
def list_published_scripts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """已发布剧本列表（id/标题/简介/人数）。"""
    scripts = (
        db.query(Script)
        .filter(Script.status == "published")
        .order_by(Script.id.desc())
        .all()
    )
    return scripts
