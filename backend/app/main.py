import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A flexible, multilingual, backend-agnostic service for mapping free-text product names to canonical inventory items. Features intelligent fuzzy matching, multi-language normalization, and interactive resolution workflow.",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize application components on startup."""
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Initialize normalizer registry with language configurations
        from app.config.loader import get_language_configs
        from app.services.matching.utils.registry import initialize_matching_utils
        from app.services.normalization.registry import initialize_normalizers

        language_configs = get_language_configs()
        logger.info(
            f"Initializing normalizers for languages: {list(language_configs.keys())}"
        )
        initialize_normalizers(language_configs)

        logger.info("Initializing matching utils")
        initialize_matching_utils(language_configs)

        logger.info("Application startup completed successfully")

    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        logger.exception("Startup error details:")
        raise
