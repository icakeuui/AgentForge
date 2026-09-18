from openai import AsyncOpenAI

from backend.core.security import decrypt_api_key, validate_provider_url
from backend.services.embedding.base import EmbeddingProvider


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key_encrypted: str,
        model: str,
        dimensions: int | None = None,
    ) -> None:
        validate_provider_url(base_url)
        self._model = model.strip()
        if not self._model:
            raise ValueError("Embedding model is required")
        self._dimensions = dimensions
        self._client = AsyncOpenAI(
            api_key=decrypt_api_key(api_key_encrypted),
            base_url=base_url.rstrip("/"),
            timeout=None,
            max_retries=0,
        )

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int | None:
        return self._dimensions

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
            dimensions=self._dimensions,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors = [list(item.embedding) for item in ordered]
        if len(vectors) != len(texts):
            raise ValueError("Embedding provider returned an unexpected vector count")
        if vectors and self._dimensions is not None and len(vectors[0]) != self._dimensions:
            raise ValueError("Embedding provider returned an unexpected vector dimension")
        return vectors

    async def validate(self) -> None:
        await self.embed_query("AgentForge embedding connectivity test")
