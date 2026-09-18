from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_current_user
from backend.core.database import get_db
from backend.models.schemas import AuthContext, AuthUserProfile, BaseResponse, PublicUserProfile
from backend.services.account_service import account_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=BaseResponse[AuthUserProfile])
async def get_current_profile(auth: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = await account_service.get_profile_for_auth(db, auth)
    return BaseResponse.success(data=profile, message="OK")


@router.get("/search/{search_id}", response_model=BaseResponse[PublicUserProfile])
async def get_public_profile(search_id: int, db: AsyncSession = Depends(get_db)):
    profile = await account_service.get_public_profile_by_search_id(db, search_id)
    return BaseResponse.success(data=profile, message="OK")
