from api.auth import router as auth_router
from api.chat import router as chat_router
from api.documents import router as documents_router
from api.downloads import router as downloads_router

__all__ = [
    "auth_router",
    "chat_router",
    "documents_router",
    "downloads_router",
]
