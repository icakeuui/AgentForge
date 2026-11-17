"""Full knowledge lifecycle against the isolated test SQLite database.

The embedding provider and Qdrant transport are deterministic stand-ins; no
external model or production collection is contacted by this test.
"""

from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import AsyncMock
import uuid

import jwt
import pytest
from docx import Document
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.core.rate_limiter import LimitStatus
from backend.models.schemas import AuthContext, GatewayResponse, RetrievalPolicy, TokenUsage
from backend.services.agent_runtime_assembler import ResolvedAgentRuntime
from backend.services.execution_log_service import execution_log_service
from backend.services.langgraph_execution_strategy import LangGraphExecutionStrategy
from backend.services.rag_retrieval_service import rag_retrieval_service


TEAM_A = "00000000-0000-0000-0000-000000000001"
TEAM_B = "00000000-0000-0000-0000-000000000002"


class FakeEmbedding:
    model_name = "isolated-embedding-v1"

    async def embed_documents(self, texts):
        return [[1.0, 0.0] for _ in texts]

    async def embed_query(self, text):
        return [0.0, 1.0] if "不存在" in text else [1.0, 0.0]


class FakeVectorStore:
    points = {}

    async def upsert(self, points, dimensions):
        assert dimensions == 2
        for point in points:
            self.points[point["id"]] = point

    async def search(self, vector, *, agent_id, model=None, limit=5):
        hits = []
        for point in self.points.values():
            payload = point["payload"]
            if payload["agent_id"] != agent_id or payload["model"] != model:
                continue
            score = sum(a * b for a, b in zip(vector, point["vector"]))
            hits.append({"id": point["id"], "payload": payload, "score": score})
        return sorted(hits, key=lambda hit: hit["score"], reverse=True)[:limit]


def headers(team=TEAM_A, user="user-integration"):
    token = jwt.encode({
        "user_id": user, "team_id": team,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }, settings.JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def make_docx(text):
    document = Document()
    document.add_paragraph(text)
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def create_agent(client, name):
    response = client.post("/agents", headers=headers(), json={
        "name": name, "description": name,
        "llm_provider_url": "https://example.com/v1",
        "llm_api_key": "isolated-test-key", "llm_model_name": "test-model",
        "embedding": {"provider": "bge_local", "model": FakeEmbedding.model_name},
        "capability_flags": {"supports_tools": False},
    })
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


@pytest.mark.asyncio
async def test_new_agent_upload_search_public_context_and_isolation(client: TestClient, monkeypatch):
    import backend.services.knowledge_ingestion_service as ingestion_module
    import backend.services.rag_retrieval_service as retrieval_module
    import backend.api.routes.public_agents as public_routes

    monkeypatch.setattr(public_routes.competition_manager_service, "check_team_rate_limit", AsyncMock(return_value=LimitStatus.ALLOWED))
    monkeypatch.setattr(public_routes.competition_manager_service, "check_team_token_limit", AsyncMock(return_value=LimitStatus.ALLOWED))

    FakeVectorStore.points = {}
    monkeypatch.setattr(ingestion_module, "create_embedding_provider", lambda _cfg: FakeEmbedding())
    monkeypatch.setattr(ingestion_module, "QdrantVectorStore", FakeVectorStore)
    monkeypatch.setattr(retrieval_module, "create_embedding_provider", lambda _cfg: FakeEmbedding())
    monkeypatch.setattr(retrieval_module, "QdrantVectorStore", FakeVectorStore)

    # Three domains, including a newly created agent with a unique fact.
    network = create_agent(client, "Network course")
    competition = create_agent(client, "Competition catalog")
    fresh = create_agent(client, "New isolated agent")
    documents = [
        (network, "network.docx", "第一章 网络基础\n互联网具有连通性和共享性两个基本特点。\n第三章 数据链路层\nCSMA/CD用于共享以太网。"),
        (competition, "catalog.docx", "省级竞赛目录收录计算机设计竞赛。"),
        (competition, "national.docx", "国家级竞赛目录收录程序设计竞赛。"),
        (fresh, "unique.docx", "蓝色彗星实验室负责海岸观测。\n它的校验词是石榴七号。"),
    ]
    for agent_id, filename, content in documents:
        response = client.post(
            f"/agents/{agent_id}/knowledge/upload", headers=headers(),
            files={"file": (filename, make_docx(content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["status"] == "ACTIVE"
        assert data["embedding_status"] == "completed"
        assert data["chunk_count"] == data["embedded_chunk_count"] > 0
        assert any(p["payload"]["document_id"] == data["id"] for p in FakeVectorStore.points.values())
        if agent_id == fresh:
            duplicate = client.post(
                f"/agents/{agent_id}/knowledge/upload", headers=headers(),
                files={"file": (filename, make_docx(content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            )
            assert duplicate.status_code == 200
            assert duplicate.json()["data"]["id"] == data["id"]

    published = client.post(f"/agents/{fresh}/publish", headers=headers(), json={"slug": "isolated-rag-test"})
    assert published.status_code == 200, published.text
    run_mock = AsyncMock()
    monkeypatch.setattr(public_routes.execution_engine, "run", run_mock)
    public = client.post("/public/agents/isolated-rag-test/execute", json={"input": "校验词是什么"})
    assert public.status_code == 200, public.text
    assert run_mock.await_args.kwargs["agent_id"] == fresh
    public_auth = run_mock.await_args.kwargs["auth_context"]
    assert public_auth.team_id == TEAM_A
    assert public_auth.auth_mode == "public_link"

    query = "蓝色彗星实验室的校验词是什么"
    config = {"embedding": {"provider": "bge_local", "model": FakeEmbedding.model_name}}
    def state(auth, agent_id=fresh, question=query):
        return {"agent_id": agent_id, "auth_context": auth, "agent_config": config,
                "user_input": question, "execution_id": uuid.uuid4()}

    preview_auth = AuthContext(user_id="user-integration", team_id=TEAM_A, auth_mode="jwt", request_id="preview")
    policy = RetrievalPolicy(retrieval_mode="required_hybrid", limit=4, min_score=2.0, required=True)
    preview = await LangGraphExecutionStrategy._retrieve_knowledge_details(state(preview_auth), retrieval_policy=policy)
    public_result = await LangGraphExecutionStrategy._retrieve_knowledge_details(state(public_auth), retrieval_policy=policy)
    assert preview["matched"] and public_result["matched"]
    assert [hit["chunk_id"] for hit in preview["knowledge_hits"]] == [hit["chunk_id"] for hit in public_result["knowledge_hits"]]
    assert "石榴七号" in preview["context"] and "unique.docx" in preview["context"]
    assert "网络" not in preview["context"] and "竞赛" not in preview["context"]
    for question in ("这个实验室的验证短语是什么？", "负责海岸观测的实验室用什么校验词？"):
        rewritten = await LangGraphExecutionStrategy._retrieve_knowledge_details(
            state(preview_auth, question=question), retrieval_policy=policy,
        )
        assert rewritten["matched"]
        assert "unique.docx" in rewritten["context"] and "石榴七号" in rewritten["context"]

    gateway = AsyncMock()
    gateway.call.return_value = GatewayResponse(
        content="校验词是石榴七号。来源：unique.docx", token_usage=TokenUsage(total_tokens=8), finish_reason="stop",
    )
    runtime = AsyncMock()
    runtime.resolve_agent_runtime.return_value = ResolvedAgentRuntime(
        agent_id=fresh, agent_config=config, supports_tools=False,
        tool_schemas=[], resolved_tool_names=[], max_steps=2, bound_tool_ids=[],
    )
    strategy = LangGraphExecutionStrategy(
        model_gateway=gateway, tool_runtime=runtime,
        execution_log_service=execution_log_service,
    )
    for auth in (preview_auth, public_auth):
        await strategy.run(agent_id=fresh, user_input=query, auth_context=auth,
                           request_id=str(uuid.uuid4()))
    assert gateway.call.await_count == 2
    for call in gateway.call.await_args_list:
        assert "石榴七号" in str(call) and "unique.docx" in str(call)

    denied = await LangGraphExecutionStrategy._retrieve_knowledge_details(
        state(AuthContext(user_id="user-team-b-1", team_id=TEAM_B, auth_mode="jwt", request_id="denied")),
        retrieval_policy=policy,
    )
    assert denied["matched"] is False
    missing = await LangGraphExecutionStrategy._retrieve_knowledge_details(
        state(preview_auth, question="知识库中不存在的卫星编号"), retrieval_policy=policy,
    )
    assert missing["matched"] is False

    # Exercise both entry identities for every domain and question shape.
    cases = (
        (network, "isolated-network-test", ("P2互联网的基本特点是什么？", "网络用户如何共享资源？", "第三章讲什么？")),
        (competition, "isolated-competition-test", ("省级目录有什么竞赛？", "全国与省级有哪些赛事？", "对比两份竞赛目录。")),
        (fresh, "isolated-rag-test", (query, "这个实验室的验证短语是什么？", "负责海岸观测的实验室用什么校验词？")),
    )
    for target_agent, slug, questions in cases:
        if target_agent != fresh:
            assert client.post(f"/agents/{target_agent}/publish", headers=headers(), json={"slug": slug}).status_code == 200
        checked = client.post(f"/public/agents/{slug}/execute", json={"input": questions[0]})
        assert checked.status_code == 200
        visitor = run_mock.await_args.kwargs["auth_context"]
        assert visitor.team_id == TEAM_A
        for question in (*questions, "知识库中不存在的紫色火星香蕉编号是什么？"):
            owner_result = await LangGraphExecutionStrategy._retrieve_knowledge_details(
                state(preview_auth, agent_id=target_agent, question=question), retrieval_policy=policy,
            )
            visitor_result = await LangGraphExecutionStrategy._retrieve_knowledge_details(
                state(visitor, agent_id=target_agent, question=question), retrieval_policy=policy,
            )
            assert [hit["chunk_id"] for hit in owner_result["knowledge_hits"]] == [
                hit["chunk_id"] for hit in visitor_result["knowledge_hits"]
            ]
            assert owner_result["matched"] is ("不存在" not in question)
            if owner_result["matched"]:
                assert all(hit["source_filename"] in owner_result["context"] for hit in owner_result["knowledge_hits"])
            forbidden = await LangGraphExecutionStrategy._retrieve_knowledge_details(
                state(AuthContext(user_id="user-team-b-1", team_id=TEAM_B, auth_mode="jwt", request_id="forbidden"),
                      agent_id=target_agent, question=question), retrieval_policy=policy,
            )
            assert forbidden["matched"] is False


@pytest.mark.asyncio
async def test_failed_index_is_hidden_and_explicit_retry_is_idempotent(client: TestClient, monkeypatch):
    import backend.services.knowledge_ingestion_service as ingestion_module
    import backend.services.rag_retrieval_service as retrieval_module

    class FailingEmbedding(FakeEmbedding):
        async def embed_documents(self, texts):
            raise RuntimeError("isolated encoder failure")

    FakeVectorStore.points = {}
    monkeypatch.setattr(ingestion_module, "create_embedding_provider", lambda _cfg: FailingEmbedding())
    monkeypatch.setattr(ingestion_module, "QdrantVectorStore", FakeVectorStore)
    monkeypatch.setattr(retrieval_module, "create_embedding_provider", lambda _cfg: FakeEmbedding())
    monkeypatch.setattr(retrieval_module, "QdrantVectorStore", FakeVectorStore)
    agent_id = create_agent(client, "Retry agent")
    uploaded = client.post(
        f"/agents/{agent_id}/knowledge/upload", headers=headers(),
        files={"file": ("retry.docx", make_docx("稳定性测试资料包含石榴七号。"),
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert uploaded.status_code == 200, uploaded.text
    data = uploaded.json()["data"]
    assert data["status"] == "FAILED" and data["embedding_status"] == "failed"
    assert data["chunk_count"] > 0 and data["embedded_chunk_count"] == 0
    search = client.post(
        f"/agents/{agent_id}/knowledge/search", headers=headers(),
        json={"query": "石榴七号"},
    )
    assert search.json()["data"] == []

    monkeypatch.setattr(ingestion_module, "create_embedding_provider", lambda _cfg: FakeEmbedding())
    retry_url = f"/agents/{agent_id}/knowledge/{data['id']}/retry-index"
    retry = client.post(retry_url, headers=headers())
    assert retry.status_code == 200, retry.text
    assert retry.json()["data"]["embedding_status"] == "completed"
    assert len(FakeVectorStore.points) == data["chunk_count"]
    assert client.post(retry_url, headers=headers()).status_code == 422
    assert client.post(
        f"/agents/{agent_id}/knowledge/search", headers=headers(),
        json={"query": "石榴七号"},
    ).json()["data"]


@pytest.mark.asyncio
async def test_large_parsed_document_indexes_after_response(client: TestClient, monkeypatch):
    import backend.services.knowledge_ingestion_service as ingestion_module
    import backend.services.rag_retrieval_service as retrieval_module

    FakeVectorStore.points = {}
    monkeypatch.setattr(ingestion_module, "create_embedding_provider", lambda _cfg: FakeEmbedding())
    monkeypatch.setattr(ingestion_module, "QdrantVectorStore", FakeVectorStore)
    monkeypatch.setattr(retrieval_module, "create_embedding_provider", lambda _cfg: FakeEmbedding())
    monkeypatch.setattr(retrieval_module, "QdrantVectorStore", FakeVectorStore)
    agent_id = create_agent(client, "Long document agent")
    content = "本章讲述石榴七号网络协议。" * 2300
    response = client.post(
        f"/agents/{agent_id}/knowledge/upload", headers=headers(),
        files={"file": ("long.docx", make_docx(content),
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["chunk_count"] > 32
    assert data["status"] == "PROCESSING"
    # TestClient drains background tasks before returning; a real HTTP client
    # sees PROCESSING first and can poll the list endpoint.
    listed = client.get(f"/agents/{agent_id}/knowledge", headers=headers()).json()["data"]
    assert listed[0]["embedding_status"] == "completed"
    assert len(FakeVectorStore.points) == data["chunk_count"]


@pytest.mark.asyncio
async def test_staged_upload_survives_request_and_deduplicates(client: TestClient, monkeypatch, tmp_path):
    import backend.services.knowledge_ingestion_service as ingestion_module
    import backend.services.rag_retrieval_service as retrieval_module
    import backend.api.routes.knowledge as knowledge_routes

    FakeVectorStore.points = {}
    monkeypatch.setattr(ingestion_module, "create_embedding_provider", lambda _cfg: FakeEmbedding())
    monkeypatch.setattr(ingestion_module, "QdrantVectorStore", FakeVectorStore)
    monkeypatch.setattr(retrieval_module, "create_embedding_provider", lambda _cfg: FakeEmbedding())
    monkeypatch.setattr(retrieval_module, "QdrantVectorStore", FakeVectorStore)
    monkeypatch.setattr(knowledge_routes, "BACKGROUND_PARSE_FILE_THRESHOLD", 1)
    monkeypatch.setattr(knowledge_routes, "STAGED_UPLOAD_DIR", tmp_path)
    agent_id = create_agent(client, "Staged upload agent")
    upload = lambda: client.post(
        f"/agents/{agent_id}/knowledge/upload", headers=headers(),
        files={"file": ("staged.docx", make_docx("独立上传事实是石榴七号。"),
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    first = upload()
    assert first.status_code == 200, first.text
    data = first.json()["data"]
    assert data["status"] == "PROCESSING"
    assert data["metadata"]["processing_stage"] == "parsing_or_ocr"
    assert (tmp_path / f"{data['id']}.bin").is_file()
    listed = client.get(f"/agents/{agent_id}/knowledge", headers=headers()).json()["data"]
    assert listed[0]["embedding_status"] == "completed"
    assert upload().json()["data"]["id"] == data["id"]
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.asyncio
async def test_staged_parse_failure_retains_file_and_marks_failed(client: TestClient, monkeypatch, tmp_path):
    import backend.api.routes.knowledge as knowledge_routes

    monkeypatch.setattr(knowledge_routes, "BACKGROUND_PARSE_FILE_THRESHOLD", 1)
    monkeypatch.setattr(knowledge_routes, "STAGED_UPLOAD_DIR", tmp_path)
    agent_id = create_agent(client, "Invalid file agent")
    response = client.post(
        f"/agents/{agent_id}/knowledge/upload", headers=headers(),
        files={"file": ("invalid.pdf", b"not a valid PDF", "application/pdf")},
    )
    assert response.status_code == 200, response.text
    document_id = response.json()["data"]["id"]
    listed = client.get(f"/agents/{agent_id}/knowledge", headers=headers()).json()["data"]
    assert listed[0]["id"] == document_id
    assert listed[0]["status"] == "FAILED"
    assert listed[0]["embedding_status"] == "failed"
    assert (tmp_path / f"{document_id}.bin").is_file()
