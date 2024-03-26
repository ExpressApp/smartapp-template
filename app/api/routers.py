"""Configuration of routers for all endpoints."""
from fastapi import APIRouter

from app.api.endpoints.botx import router as bot_router
from app.api.endpoints.healthcheck import router as healthcheck_router
from app.api.endpoints.swagger_rpc_execute import router as swagger_rpc_execute_router
from app.settings import settings

router = APIRouter(include_in_schema=False)

router.include_router(healthcheck_router)
router.include_router(bot_router)

if settings.DEBUG:
    router.include_router(swagger_rpc_execute_router)
