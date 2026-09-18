from __future__ import annotations

import random

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.orm import SearchIdAllocation


class SearchIdService:
    async def allocate(self, session: AsyncSession, user_id: str) -> int:
        for _ in range(128):
            candidate = random.randint(settings.SEARCH_ID_MIN, settings.SEARCH_ID_MAX)
            existing = await session.execute(select(SearchIdAllocation).where(SearchIdAllocation.search_id == candidate))
            if existing.scalar_one_or_none() is not None:
                continue

            allocation = SearchIdAllocation(search_id=candidate, user_id=user_id)
            try:
                async with session.begin_nested():
                    session.add(allocation)
                    await session.flush()
                return candidate
            except IntegrityError:
                continue
        raise RuntimeError("Unable to allocate search id")

    async def get_user_id(self, session: AsyncSession, search_id: int) -> str | None:
        result = await session.execute(select(SearchIdAllocation).where(SearchIdAllocation.search_id == search_id))
        allocation = result.scalar_one_or_none()
        return None if allocation is None else allocation.user_id


search_id_service = SearchIdService()
