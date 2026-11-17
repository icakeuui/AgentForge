"""Exercise the real Qdrant SDK against its isolated in-memory store."""

import uuid

import pytest
from qdrant_client import AsyncQdrantClient

from backend.services.vector_store.qdrant_store import QdrantVectorStore


@pytest.mark.asyncio
async def test_qdrant_write_wait_and_agent_model_filter():
    client = AsyncQdrantClient(":memory:")
    store = object.__new__(QdrantVectorStore)
    store._client = client
    store._collection = "isolated_rag_regression"
    own = str(uuid.uuid4())
    other = str(uuid.uuid4())
    points = [
        {"id": str(uuid.uuid4()), "vector": [1.0, 0.0],
         "payload": {"agent_id": own, "model": "model-a", "chunk_id": str(uuid.uuid4())}},
        {"id": str(uuid.uuid4()), "vector": [1.0, 0.0],
         "payload": {"agent_id": other, "model": "model-a", "chunk_id": str(uuid.uuid4())}},
        {"id": str(uuid.uuid4()), "vector": [1.0, 0.0],
         "payload": {"agent_id": own, "model": "model-b", "chunk_id": str(uuid.uuid4())}},
    ]
    await store.upsert(points, dimensions=2)
    assert (await client.get_collection(store._collection)).points_count == 3
    own_hits = await store.search([1.0, 0.0], agent_id=own, model="model-a")
    assert [hit["id"] for hit in own_hits] == [points[0]["id"]]
    assert await store.search([1.0, 0.0], agent_id=str(uuid.uuid4()), model="model-a") == []
    with pytest.raises(ValueError, match="vector size"):
        await store.upsert([{"id": str(uuid.uuid4()), "vector": [1.0] }], dimensions=1)
    await client.close()
