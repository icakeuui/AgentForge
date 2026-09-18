from fastapi import APIRouter, Depends
from backend.models.schemas import AuthContext, BaseResponse, TeamQuotaStatusData
from backend.api.dependencies import get_current_user
from backend.services.authorization_service import authorization_service
from backend.services.competition_manager_service import competition_manager_service

router = APIRouter(prefix="/teams", tags=["Teams"])

@router.get("/{team_id}/quota", response_model=BaseResponse[TeamQuotaStatusData])
async def get_team_quota(
    team_id: str, 
    auth: AuthContext = Depends(get_current_user),
):
    await authorization_service.ensure_quota_context_ownership(auth, team_id)
    quota = await competition_manager_service.get_team_quota_status(
        team_id=team_id
    )
    return BaseResponse.success(data=quota, message="OK")
