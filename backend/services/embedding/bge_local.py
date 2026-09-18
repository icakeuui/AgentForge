from __future__ import annotations

import asyncio
import threading
from typing import Any

from backend.services.embedding.base import EmbeddingProvider


class BGEEmbeddingProvider(EmbeddingProvider):
    """Local BGE provider with a process-level model cache."""

    DEFAULT_MODEL = "BAAI/bge-large-zh-v1.5"
    _models: dict[tuple[str, str], Any] = {}
    _lock = threading.Lock()

    def __init__(self, *, model: str | None = None) -> None:
        self._model = (model or self.DEFAULT_MODEL).strip()
        if not self._model:
            raise ValueError("Local BGE model is required")
        self._device = self._detect_device()
        self._encoder = self._get_or_load_model(self._model, self._device)
        self._dimensions = int(self._encoder.get_sentence_embedding_dimension())

    @staticmethod
    def _detect_device() -> str:
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    @classmethod
    def _get_or_load_model(cls, model_name: str, device: str) -> Any:
        key = (model_name, device)
        if key in cls._models:
            return cls._models[key]
        with cls._lock:
            if key in cls._models:
                return cls._models[key]
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError("当前环境缺少 sentence-transformers，无法加载本地 BGE 模型") from exc
            encoder = SentenceTransformer(model_name, device=device)
            cls._models[key] = encoder
            return encoder

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int | None:
        return self._dimensions

    @property
    def device(self) -> str:
        return self._device

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = await asyncio.to_thread(
            self._encoder.encode,
            texts,
            batch_size=32,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    async def validate(self) -> None:
        vectors = await self.embed_documents(["AgentForge 本地向量模型连接测试"])
        if not vectors or len(vectors[0]) != self._dimensions:
            raise ValueError("本地 BGE 模型返回的向量维度无效")
