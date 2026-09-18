from abc import ABC, abstractmethod
from typing import Any


class VectorStore(ABC):
    @abstractmethod
    async def ensure_collection(self, dimensions: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def upsert(self, points: list[dict[str, Any]], dimensions: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def search(
        self, vector: list[float], *, agent_id: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def delete_document(self, document_id: str) -> None:
        raise NotImplementedError
