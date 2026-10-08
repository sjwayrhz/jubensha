from fastapi import APIRouter

from .admin import router as admin_router
from .auth import router as auth_router
from .chat import router as chat_router
from .dm import router as dm_router
from .rooms import router as rooms_router
from .scripts import router as scripts_router
from .voice import router as voice_router
from .ws import router as ws_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(scripts_router)
router.include_router(dm_router)
router.include_router(rooms_router)
router.include_router(chat_router)
router.include_router(voice_router)
router.include_router(ws_router)
