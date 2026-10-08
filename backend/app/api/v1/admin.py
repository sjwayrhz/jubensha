from fastapi import APIRouter, Depends

from ...core.deps import require_admin
from ...models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/scripts")
def list_scripts(admin: User = Depends(require_admin)):
    """剧本列表（占位）。二期：上传/解析/发布管线。"""
    return {"items": [], "total": 0}
