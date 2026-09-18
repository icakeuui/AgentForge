from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Provider-neutral interface used by ingestion and RAG retrieval."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def dimensions(self) -> int | None:
        raise NotImplementedError

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_documents([text])
        if not vectors:
            raise ValueError("Embedding provider returned no vector")
        return vectors[0]

    @abstractmethod
    async def validate(self) -> None:
        raise NotImplementedError
