from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api.middleware import RequestLoggingMiddleware
from backend.api.routes.agents import router as agents_router
from backend.api.routes.auth import router as auth_router
from backend.api.routes.executions import router as executions_router
from backend.api.routes.health import router as health_router
from backend.api.routes.knowledge import router as knowledge_router
from backend.api.routes.public_agents import router as public_agents_router
from backend.api.routes.sandbox import router as sandbox_router
from backend.api.routes.users import router as users_router
from backend.api.routes.teams import router as teams_router
from backend.api.routes.tools import router as tools_router
from backend.core.config import PROJECT_ROOT, settings
from backend.core import database as core_db
from backend.core.exceptions import AgentForgeBaseException
from backend.core.logging import logger, setup_logging
from backend.core.tool_runtime import ToolRegistry
from backend.core.tools import CalculateTool, EchoTool, PythonAddTool, PythonExecutorTool, WebSearchTool
from backend.models.constants import ResponseCode
from backend.models.schemas import BaseResponse
from backend.services.marketplace_tool_adapter import marketplace_tool_adapter
from backend.services.schema_migration_service import ensure_auth_columns, ensure_knowledge_governance_columns
import backend.models.orm  # noqa: F401 - registers ORM tables
from plugin_marketplace import MarketplaceAPI
from plugin_marketplace.api.routes import create_router as create_marketplace_router
from plugin_marketplace.db.database import init_db as init_pm_db
import plugin_marketplace.db.models  # noqa: F401 - registers marketplace tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    async with core_db.engine.begin() as conn:
        await conn.run_sync(core_db.Base.metadata.create_all)
    await ensure_auth_columns(core_db.engine)
    await ensure_knowledge_governance_columns(core_db.engine)
    await init_pm_db(core_db.engine)
    await ensure_knowledge_governance_columns(core_db.engine)
    logger.info("Database tables initialized.")

    existing_registry = getattr(app.state, "tool_registry", None)
    if existing_registry is None:
        logger.info("Registering tools...")
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(PythonAddTool())
        registry.register(PythonExecutorTool())
        registry.register(CalculateTool())
        registry.register(WebSearchTool())
        registry.lock()
        app.state.tool_registry = registry
        logger.info("Tool registry locked.")
    else:
        logger.info("Tool registry already initialized, skipping re-registration.")

    logger.info("Initializing plugin marketplace...")
    pm_api = MarketplaceAPI(
        database_url=settings.DB_URL,
        session_factory=core_db.AsyncSessionLocal,
    )
    await pm_api.initialize()
    app.state.pm_api = pm_api
    marketplace_tool_adapter._marketplace_api = pm_api
    logger.info("Plugin marketplace initialized.")

    try:
        yield
    finally:
        pm_api = getattr(app.state, "pm_api", None)
        if pm_api is not None:
            await pm_api.close()


def create_app() -> FastAPI:
    uploads_dir = PROJECT_ROOT / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title=settings.APP_NAME,
        description="AgentForge Backend Engine",
        version="1.0",
        lifespan=lifespan,
    )

    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} in {settings.ENV} mode")
    logger.info(
        f"Config loaded: ENV={settings.ENV}, APP_NAME={settings.APP_NAME}, LOG_LEVEL={settings.LOG_LEVEL}"
    )
    if settings.AUTH_DEV_BYPASS_ENABLED and not settings.is_dev_env:
        raise RuntimeError("AUTH_DEV_BYPASS_ENABLED is only allowed in local/development environments")

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    @app.exception_handler(AgentForgeBaseException)
    async def agent_forge_exception_handler(request: Request, exc: AgentForgeBaseException):
        logger.warning(f"AgentForge Exception: {exc.message} (Code: {exc.code}, Status: {exc.status_code})")
        return JSONResponse(
            status_code=exc.status_code,
            content=BaseResponse.error(
                code=exc.code,
                message=exc.message,
                data=exc.data,
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation Error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content=BaseResponse.error(
                code=ResponseCode.VALIDATION_ERROR,
                message="Schema validation failed. Check request body format and required fields.",
            ).model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(f"HTTP Exception: {exc.detail} (Status: {exc.status_code})")

        code = ResponseCode.INTERNAL_ERROR
        if exc.status_code == 404:
            code = ResponseCode.NOT_FOUND
        elif exc.status_code == 401:
            code = ResponseCode.AUTH_REQUIRED
        elif exc.status_code == 403:
            code = ResponseCode.PERMISSION_DENIED
        elif exc.status_code == 429:
            code = ResponseCode.RATE_LIMIT_EXCEEDED

        return JSONResponse(
            status_code=exc.status_code,
            content=BaseResponse.error(
                code=code,
                message=exc.detail,
            ).model_dump(),
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.exception(f"Database Error: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content=BaseResponse.error(
                code=ResponseCode.DATABASE_ERROR,
                message="A database error occurred. Operation could not be completed.",
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled Exception: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content=BaseResponse.error(
                code=ResponseCode.INTERNAL_ERROR,
                message="An unexpected error occurred",
            ).model_dump(),
        )

    app.include_router(health_router, prefix="", tags=["Monitoring"])
    app.include_router(agents_router, prefix="", tags=["Agents"])
    app.include_router(auth_router, prefix="", tags=["Auth"])
    app.include_router(users_router, prefix="", tags=["Users"])
    app.include_router(sandbox_router, prefix="", tags=["Sandbox"])
    app.include_router(tools_router, prefix="", tags=["Tools"])
    app.include_router(knowledge_router, prefix="", tags=["Knowledge"])
    app.include_router(executions_router, prefix="", tags=["Executions"])
    app.include_router(teams_router, prefix="", tags=["Teams"])
    app.include_router(public_agents_router, prefix="", tags=["Public Agents"])
    app.include_router(create_marketplace_router(), prefix="", tags=["Plugin Marketplace"])

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=(settings.ENV == "dev"),
    )
