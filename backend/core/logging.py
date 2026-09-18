import sys
from contextvars import ContextVar
from loguru import logger
from backend.core.config import settings

REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="system")
TEAM_ID: ContextVar[str] = ContextVar("team_id", default="")
USER_ID: ContextVar[str] = ContextVar("user_id", default="")
AUTH_MODE: ContextVar[str] = ContextVar("auth_mode", default="unknown")
PATH: ContextVar[str] = ContextVar("path", default="")
RESOURCE_TYPE: ContextVar[str] = ContextVar("resource_type", default="")
RESOURCE_ID: ContextVar[str] = ContextVar("resource_id", default="")

def setup_logging():
    # Remove default handler
    logger.remove()
    
    # Custom format with automatic request_id from patcher
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<yellow>[req={extra[request_id]} user={extra[user_id]} team={extra[team_id]} mode={extra[auth_mode]} "
        "path={extra[path]} resource_type={extra[resource_type]} resource_id={extra[resource_id]}]</yellow> - "
        "<level>{message}</level>"
    )
    
    # Add console handler
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=True
    )

# Patcher to automatically pull request_id from ContextVar
def request_id_patcher(record):
    record["extra"].setdefault("request_id", REQUEST_ID.get())
    record["extra"].setdefault("team_id", TEAM_ID.get())
    record["extra"].setdefault("user_id", USER_ID.get())
    record["extra"].setdefault("auth_mode", AUTH_MODE.get())
    record["extra"].setdefault("path", PATH.get())
    record["extra"].setdefault("resource_type", RESOURCE_TYPE.get())
    record["extra"].setdefault("resource_id", RESOURCE_ID.get())

# Configure logger with the patcher for all future logs
logger.configure(patcher=request_id_patcher)

def set_request_id(request_id: str):
    REQUEST_ID.set(request_id)

def get_request_id() -> str:
    return REQUEST_ID.get()

def set_team_id(team_id: str):
    TEAM_ID.set(team_id)

def get_team_id() -> str:
    return TEAM_ID.get()

def set_user_id(user_id: str):
    USER_ID.set(user_id)

def get_user_id() -> str:
    return USER_ID.get()

def set_auth_mode(auth_mode: str):
    AUTH_MODE.set(auth_mode)

def get_auth_mode() -> str:
    return AUTH_MODE.get()

def set_path(path: str):
    PATH.set(path)

def get_path() -> str:
    return PATH.get()

def set_resource_type(resource_type: str):
    RESOURCE_TYPE.set(resource_type)

def get_resource_type() -> str:
    return RESOURCE_TYPE.get()

def set_resource_id(resource_id: str):
    RESOURCE_ID.set(resource_id)

def get_resource_id() -> str:
    return RESOURCE_ID.get()
