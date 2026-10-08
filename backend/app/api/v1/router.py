from fastapi import APIRouter

from .admin import router as admin_router
from .auth import router as auth_router
from .scripts import router as scripts_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(scripts_router)
