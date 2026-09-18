from fastapi import APIRouter
from backend.models.schemas import BaseResponse
import time

router = APIRouter()

@router.get("/health", response_model=BaseResponse)
async def health_check():
    """
    基础健康检查接口 (Liveness Probe)。
    用于 Kubernetes 或 Docker 检查服务实例是否存活。
    """
    return BaseResponse.success(
        data={
            "status": "healthy",
            "timestamp": time.time(),
            "service": "AgentForge-Backend",
            "version": "1.0"
        },
        message="Service liveness check passed"
    )
