"""
plugin_marketplace.api.routes
FastAPI routes for the plugin marketplace.
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from backend.api.dependencies import get_current_user
from backend.core.logging import logger
from backend.core.exceptions import PermissionException, ValidationException
from backend.models.schemas import AuthContext
from backend.services.authorization_service import authorization_service

from plugin_marketplace.api.schemas import (
    ExtensionListItem,
    ExtensionDetail,
    ToolListItem,
    ToolExecuteRequest,
    ToolExecuteResponse,
    AgentToolBindRequest,
    ExtensionInstallRequest,
    ExtensionInstallResponse,
    UserExtensionItem,
    ExtensionConnectionTestRequest,
    ExtensionConnectionTestResponse,
)
from plugin_marketplace.exceptions import ToolBindingValidationError
def create_router() -> APIRouter:
    """
    Create and return the plugin marketplace FastAPI router.
    """
    router = APIRouter(prefix="/api/v1/marketplace", tags=["Plugin Marketplace"])

    def _marketplace_api(request: Request):
        api = getattr(request.app.state, "pm_api", None)
        if api is None:
            raise HTTPException(status_code=503, detail="Plugin marketplace is not initialized")
        return api

    @router.get("/extensions", response_model=list[ExtensionListItem])
    async def list_extensions(request: Request, auth: AuthContext = Depends(get_current_user)):
        """List all available extensions."""
        try:
            marketplace_api = _marketplace_api(request)
            items = await marketplace_api.list_extensions()
            return [ExtensionListItem(**item) for item in items]
        except PermissionException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/extensions/{extension_id}", response_model=ExtensionDetail)
    async def get_extension(extension_id: str, request: Request, auth: AuthContext = Depends(get_current_user)):
        """Get extension details with tools."""
        try:
            marketplace_api = _marketplace_api(request)
            tools = await marketplace_api.list_extension_tools(extension_id)
            extensions = await marketplace_api.list_extensions()
            ext = next((e for e in extensions if e["id"] == extension_id), None)
            if not ext:
                raise HTTPException(status_code=404, detail=f"Extension {extension_id} not found")
            ext["tools"] = tools
            return ExtensionDetail(**ext)
        except HTTPException:
            raise
        except PermissionException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/extensions/{extension_id}/tools", response_model=list[ToolListItem])
    async def list_extension_tools(extension_id: str, request: Request, auth: AuthContext = Depends(get_current_user)):
        """List tools for an extension."""
        try:
            marketplace_api = _marketplace_api(request)
            tools = await marketplace_api.list_extension_tools(extension_id)
            return [ToolListItem(**t) for t in tools]
        except PermissionException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/extensions/{extension_id}/install", response_model=ExtensionInstallResponse)
    async def install_extension(
        extension_id: str,
        request: Request,
        payload: ExtensionInstallRequest,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Install an extension for a user."""
        try:
            await authorization_service.ensure_extension_installation_scope(
                auth, payload.user_id, extension_id
            )
            marketplace_api = _marketplace_api(request)
            await marketplace_api.install_extension(extension_id, payload.user_id, payload.config)
            logger.bind(
                resource_type="extension_installation",
                resource_id=extension_id,
            ).info(f"resource access log: install extension {extension_id}")
            return ExtensionInstallResponse(
                extension_id=extension_id,
                status="installed",
                message="ok",
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except PermissionException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("/extensions/{extension_id}/uninstall")
    async def uninstall_extension(
        extension_id: str,
        user_id: str,
        request: Request,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Uninstall an extension for a user."""
        try:
            await authorization_service.ensure_user_extension_ownership(auth, user_id, extension_id)
            marketplace_api = _marketplace_api(request)
            await marketplace_api.uninstall_extension(extension_id, user_id)
            logger.bind(
                resource_type="extension_installation",
                resource_id=extension_id,
            ).info(f"resource access log: uninstall extension {extension_id}")
            return {"status": "ok"}
        except PermissionException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/extensions/{extension_id}/test-connection", response_model=ExtensionConnectionTestResponse)
    async def test_extension_connection(
        extension_id: str,
        request: Request,
        payload: ExtensionConnectionTestRequest,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Validate user-supplied configuration for an extension."""
        try:
            marketplace_api = _marketplace_api(request)
            result = await marketplace_api.test_extension_connection(extension_id, payload.config)
            return ExtensionConnectionTestResponse(**result)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except PermissionException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/users/{user_id}/extensions", response_model=list[UserExtensionItem])
    async def list_user_extensions(
        user_id: str,
        request: Request,
        auth: AuthContext = Depends(get_current_user),
    ):
        """List extensions installed for a user."""
        try:
            await authorization_service.ensure_extension_installation_scope(auth, user_id, "*")
            marketplace_api = _marketplace_api(request)
            items = await marketplace_api.list_user_extensions(user_id)
            logger.bind(
                resource_type="extension_installation",
                resource_id=user_id,
            ).info(f"resource access log: list user extensions user={user_id}")
            return [UserExtensionItem(**item) for item in items]
        except PermissionException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/tools/execute", response_model=ToolExecuteResponse)
    async def execute_tool(
        payload: ToolExecuteRequest,
        request: Request,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Execute a tool."""
        try:
            context = payload.context or {}
            context_user_id = context.get("user_id")
            if context_user_id:
                await authorization_service.ensure_extension_installation_scope(
                    auth, context_user_id, payload.tool_id.split("/", 1)[0]
                )
            payload.context = {
                **context,
                "user_id": auth.user_id,
                "team_id": auth.team_id,
                "request_id": getattr(request.state, "request_id", ""),
            }
            marketplace_api = _marketplace_api(request)
            result = await marketplace_api.execute_tool(
                payload.tool_id,
                payload.arguments,
                payload.context,
            )
            logger.bind(
                resource_type="tool_binding",
                resource_id=payload.tool_id,
            ).info(f"execution trace log: marketplace execute tool {payload.tool_id}")
            return ToolExecuteResponse(result=result)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except PermissionException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/agents/{agent_id}/tools")
    async def get_agent_tools(
        agent_id: str,
        request: Request,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Get all tools bound to an agent."""
        try:
            await authorization_service.ensure_agent_ownership(auth, uuid.UUID(agent_id), operation="query_tools")
            marketplace_api = _marketplace_api(request)
            tools = await marketplace_api.get_tools_for_agent(agent_id)
            logger.bind(
                resource_type="tool_binding",
                resource_id=agent_id,
            ).info(f"resource access log: query bound tools agent={agent_id}")
            return {"tools": tools}
        except PermissionException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/agents/{agent_id}/tools/bind")
    async def bind_tools(
        agent_id: str,
        payload: AgentToolBindRequest,
        request: Request,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Bind tools to an agent."""
        try:
            await authorization_service.ensure_agent_ownership(auth, uuid.UUID(agent_id), operation="bind_tools")
            marketplace_api = _marketplace_api(request)
            result = await marketplace_api.bind_tools_to_agent(agent_id, payload.tool_ids)
            logger.bind(
                resource_type="tool_binding",
                resource_id=agent_id,
            ).info(f"resource access log: bind tools for agent={agent_id}")
            return {
                "status": "ok",
                "result_status": result.status,
                "agent_id": agent_id,
                "bound": len(result.bound_tool_ids),
                "already_bound": len(result.already_bound_tool_ids),
                "resolved_tool_ids": result.resolved_tool_ids,
            }
        except ToolBindingValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except ValidationException:
            raise
        except PermissionException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("/agents/{agent_id}/tools/{tool_id:path}")
    async def unbind_tool(
        agent_id: str,
        tool_id: str,
        request: Request,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Unbind a tool from an agent."""
        try:
            await authorization_service.ensure_agent_ownership(auth, uuid.UUID(agent_id), operation="unbind_tool")
            marketplace_api = _marketplace_api(request)
            result = await marketplace_api.unbind_tools_from_agent(agent_id, [tool_id])
            logger.bind(
                resource_type="tool_binding",
                resource_id=agent_id,
            ).info(f"resource access log: unbind tool for agent={agent_id}")
            return {"status": "ok", "result_status": result.status, "unbound": len(result.unbound_tool_ids)}
        except ToolBindingValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except ValidationException:
            raise
        except PermissionException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/tools/schemas")
    async def get_tool_schemas(request: Request, auth: AuthContext = Depends(get_current_user)):
        """Get all tool schemas in OpenAI function-calling format."""
        try:
            marketplace_api = _marketplace_api(request)
            schemas = await marketplace_api.get_tool_schemas()
            return {"tools": schemas}
        except PermissionException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router
