from typing import Any

from backend.core.config import settings
from backend.services.vector_store.base import VectorStore


class QdrantVectorStore(VectorStore):
    def __init__(self) -> None:
        try:
            from qdrant_client import AsyncQdrantClient
        except ImportError as exc:
            raise RuntimeError("当前环境缺少 qdrant-client，无法写入向量库") from exc
        kwargs: dict[str, Any] = {"url": settings.QDRANT_URL}
        if settings.QDRANT_API_KEY:
            kwargs["api_key"] = settings.QDRANT_API_KEY
        self._client = AsyncQdrantClient(**kwargs)
        self._collection = settings.QDRANT_COLLECTION

    async def ensure_collection(self, dimensions: int) -> None:
        from qdrant_client import models

        exists = await self._client.collection_exists(self._collection)
        if not exists:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=models.VectorParams(
                    size=dimensions,
                    distance=models.Distance.COSINE,
                ),
            )
        else:
            info = await self._client.get_collection(self._collection)
            configured = info.config.params.vectors
            if isinstance(configured, dict) or configured.size != dimensions:
                raise ValueError(
                    f"Qdrant collection vector size does not match embedding size {dimensions}"
                )

    async def upsert(self, points: list[dict[str, Any]], dimensions: int) -> None:
        from qdrant_client import models

        if not points:
            return
        await self.ensure_collection(dimensions)
        await self._client.upsert(
            collection_name=self._collection,
            wait=True,
            points=[
                models.PointStruct(
                    id=point["id"],
                    vector=point["vector"],
                    payload=point.get("payload", {}),
                )
                for point in points
            ],
        )

    async def search(
        self, vector: list[float], *, agent_id: str, model: str | None = None, limit: int = 5
    ) -> list[dict[str, Any]]:
        from qdrant_client import models

        conditions = [models.FieldCondition(key="agent_id", match=models.MatchValue(value=agent_id))]
        if model:
            conditions.append(models.FieldCondition(key="model", match=models.MatchValue(value=model)))
        query_filter = models.Filter(must=conditions)
        if hasattr(self._client, "search"):
            results = await self._client.search(
                collection_name=self._collection,
                query_vector=vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
        else:
            response = await self._client.query_points(
                collection_name=self._collection,
                query=vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
            results = response.points
        return [
            {"id": str(item.id), "score": item.score, "payload": item.payload or {}}
            for item in results
        ]

    async def delete_document(self, document_id: str) -> None:
        from qdrant_client import models

        await self._client.delete(
            collection_name=self._collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
                )
            ),
        )
