from fastapi import APIRouter

from app.api.routes import backends, login, matching, private, users, utils
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(matching.router, prefix="/matching", tags=["matching"])
api_router.include_router(backends.router, prefix="/backend", tags=["backends"])


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
