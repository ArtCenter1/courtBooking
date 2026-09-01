from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.credentials import router as credentials_router
from app.api.tasks import router as tasks_router
from app.api.scanner import router as scanner_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(credentials_router)
api_router.include_router(tasks_router)
api_router.include_router(scanner_router)

__all__ = ["api_router"]
