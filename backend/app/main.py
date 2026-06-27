import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings, reload_settings
from app.core.middleware import setup_exception_handlers, setup_middleware
from app.core.responses import success_response
from app.db.indexes import create_indexes
from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = reload_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    cfg = reload_settings()
    gemini_ok = bool(cfg.gemini_api_key)
    openai_ok = bool(cfg.openai_api_key)
    logger.info(
        "AI config: provider=%s gemini=%s openai=%s",
        cfg.ai_provider,
        "configured" if gemini_ok else "missing",
        "configured" if openai_ok else "missing",
    )
    await connect_to_mongo()
    await create_indexes(get_database())
    logger.info("SmartStudy API started")
    yield
    from app.services.ai.base_provider import close_http_client

    await close_http_client()
    await close_mongo_connection()
    logger.info("SmartStudy API stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="SmartStudy - AI-powered exam preparation platform API",
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )

    setup_middleware(app)
    setup_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["System"], summary="Health check")
    async def health_check():
        return success_response(
            {
                "status": "healthy",
                "app": settings.app_name,
                "version": settings.app_version,
                "environment": settings.environment,
            }
        )

    return app


app = create_app()
