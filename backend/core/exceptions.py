from typing import Any, Optional
from backend.models.constants import ResponseCode

class AgentForgeBaseException(Exception):
    """Base exception for all AgentForge errors."""
    def __init__(
        self, 
        message: str, 
        code: ResponseCode = ResponseCode.INTERNAL_ERROR,
        status_code: int = 500,
        data: Optional[Any] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.data = data
        super().__init__(self.message)

class AuthException(AgentForgeBaseException):
    def __init__(self, message: str, code: ResponseCode = ResponseCode.AUTH_REQUIRED):
        super().__init__(message, code=code, status_code=401)

class PermissionException(AgentForgeBaseException):
    def __init__(self, message: str, code: ResponseCode = ResponseCode.PERMISSION_DENIED):
        super().__init__(message, code=code, status_code=403)

class NotFoundException(AgentForgeBaseException):
    def __init__(self, message: str):
        super().__init__(message, code=ResponseCode.NOT_FOUND, status_code=404)

class ValidationException(AgentForgeBaseException):
    def __init__(self, message: str):
        super().__init__(message, code=ResponseCode.VALIDATION_ERROR, status_code=422)


class FlowException(AgentForgeBaseException):
    def __init__(self, message: str, code: ResponseCode = ResponseCode.INTERNAL_ERROR, data: Optional[Any] = None, status_code: int = 400):
        super().__init__(message, code=code, status_code=status_code, data=data)


class QuotaException(AgentForgeBaseException):
    def __init__(self, message: str, code: ResponseCode = ResponseCode.QUOTA_EXCEEDED):
        super().__init__(message, code=code, status_code=429)

class ModelGatewayException(AgentForgeBaseException):
    def __init__(
        self,
        message: str,
        code: ResponseCode = ResponseCode.MODEL_ERROR,
        status_code: int = 502,
        data: Optional[Any] = None,
    ):
        super().__init__(message, code=code, status_code=status_code, data=data)

class ToolRuntimeException(AgentForgeBaseException):
    def __init__(self, message: str):
        super().__init__(message, code=ResponseCode.TOOL_ERROR, status_code=500)

class SandboxException(AgentForgeBaseException):
    def __init__(self, message: str):
        super().__init__(message, code=ResponseCode.SANDBOX_ERROR, status_code=500)

class EngineException(AgentForgeBaseException):
    def __init__(self, message: str):
        super().__init__(message, code=ResponseCode.ENGINE_ERROR, status_code=500)
