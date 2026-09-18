from typing import Any

from backend.services.embedding.base import EmbeddingProvider
from backend.services.embedding.openai_compatible import OpenAICompatibleEmbeddingProvider
from backend.services.embedding.bge_local import BGEEmbeddingProvider


def create_embedding_provider(config: dict[str, Any]) -> EmbeddingProvider:
    provider = str(config.get("provider", "openai_compatible")).strip().lower()
    if provider == "bge_local":
        return BGEEmbeddingProvider(model=str(config.get("model") or BGEEmbeddingProvider.DEFAULT_MODEL))
    if provider != "openai_compatible":
        raise ValueError(f"Unsupported embedding provider: {provider}")
    return OpenAICompatibleEmbeddingProvider(
        base_url=str(config.get("base_url", "")),
        api_key_encrypted=str(config.get("api_key_encrypted", "")),
        model=str(config.get("model", "")),
        dimensions=config.get("dimensions"),
    )
