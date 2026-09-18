import jwt
from typing import Optional
from fastapi import Header, Depends, Request
from backend.core.config import settings
from backend.core.logging import logger, set_team_id, set_user_id, set_auth_mode
from backend.services.competition_manager_service import competition_manager_service
from backend.services.authorization_service import authorization_service
from backend.core.exceptions import AuthException, PermissionException
from backend.models.constants import ResponseCode
from backend.models.schemas import AuthContext

async def resolve_auth_context(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> AuthContext:
    logger.bind(
        path=request.url.path,
        resource_type="auth_entry",
        resource_id="*",
    ).info(f"auth entry log: {request.method} {request.url.path}")
    request_id = getattr(request.state, "request_id", "")

    if settings.auth_dev_bypass_enabled:
        if not settings.is_dev_env:
            logger.bind(
                path=request.url.path,
                resource_type="auth_dev_bypass",
                resource_id="*",
            ).error("dev bypass configured outside local/development environment")
            raise AuthException("Dev bypass is not allowed in this environment", code=ResponseCode.TOKEN_INVALID)

        auth = AuthContext(
            user_id=settings.AUTH_DEV_USER_ID,
            team_id=settings.AUTH_DEV_TEAM_ID,
            auth_mode="dev_bypass",
            request_id=request_id,
            role=settings.AUTH_DEV_ROLE,
            is_dev=True,
            search_id=0,
            email="dev@example.local",
            email_verified=True,
        )
        set_user_id(auth.user_id)
        set_team_id(auth.team_id)
        set_auth_mode(auth.auth_mode)
        logger.bind(
            path=request.url.path,
            resource_type="auth_dev_bypass",
            resource_id=auth.user_id,
        ).info("dev bypass hit log")
        return auth

    if not authorization or not authorization.startswith("Bearer "):
        raise AuthException("Authorization required", code=ResponseCode.AUTH_REQUIRED)

    token = authorization[7:]
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        logger.bind(
            path=request.url.path,
            resource_type="jwt_validation",
            resource_id="*",
        ).warning("jwt validation failed log: token expired")
        raise AuthException("Token expired", code=ResponseCode.TOKEN_EXPIRED)
    except jwt.InvalidTokenError:
        logger.bind(
            path=request.url.path,
            resource_type="jwt_validation",
            resource_id="*",
        ).warning("jwt validation failed log: invalid token")
        raise AuthException("Invalid token", code=ResponseCode.TOKEN_INVALID)

    user_id = payload.get("user_id") or payload.get("sub")
    team_id = payload.get("team_id")
    role = payload.get("role", "member")
    search_id_raw = payload.get("search_id")
    email = payload.get("email")
    email_verified = bool(payload.get("email_verified", False))

    if not user_id or not team_id:
        logger.bind(
            path=request.url.path,
            resource_type="jwt_validation",
            resource_id="*",
        ).warning("jwt validation failed log: missing user_id/team_id claim")
        raise AuthException("Invalid token payload: missing user_id or team_id", code=ResponseCode.TOKEN_INVALID)

    auth = AuthContext(
        user_id=str(user_id),
        team_id=str(team_id),
        auth_mode="jwt",
        request_id=request_id,
        role=str(role),
        is_dev=False,
        search_id=int(search_id_raw) if isinstance(search_id_raw, int) or (isinstance(search_id_raw, str) and search_id_raw.isdigit()) else None,
        email=str(email) if isinstance(email, str) else None,
        email_verified=email_verified,
    )
    set_user_id(auth.user_id)
    set_team_id(auth.team_id)
    set_auth_mode(auth.auth_mode)
    return auth

async def get_current_user(
    auth: AuthContext = Depends(resolve_auth_context),
) -> AuthContext:
    if auth.is_dev and auth.auth_mode == "dev_bypass":
        return auth
    await authorization_service.validate_membership(auth)
    return auth

async def verify_team_permission(
    team_id: str,
    auth: AuthContext = Depends(get_current_user)
) -> str:
    """
    Authorization dependency.
    Verifies if the current user belongs to the target team.
    """
    team = await competition_manager_service.get_team(team_id)
    if not team:
        raise PermissionException(f"Team {team_id} not found", code=ResponseCode.TEAM_FORBIDDEN)
    if auth.team_id != team_id:
        logger.bind(
            resource_type="runtime_quota_context",
            resource_id=team_id,
        ).warning("permission denied log: cross-team team permission")
        raise PermissionException(
            f"Access denied: Team {auth.team_id} cannot access resources of Team {team_id}",
            code=ResponseCode.TEAM_FORBIDDEN
        )
    return team_id
