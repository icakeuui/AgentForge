# AgentForge

AgentForge 是一个面向单智能体应用的本地开发平台，提供 Agent 配置、Chat 模型调用、工具执行、知识库、RAG 检索、执行日志、权限认证和公开 Agent 链接。

当前实现包括：FastAPI 后端、React/Vite 前端、OpenAI-compatible Chat Gateway、DeepSeek/OpenAI-compatible 模型接入、PDF/DOCX/TXT 知识库、本地 BGE Embedding、Qdrant 向量存储和 LangGraph Agent 执行。

## 技术栈

| 类型 | 实现 |
| --- | --- |
| 后端 | FastAPI、Uvicorn、Pydantic Settings |
| 前端 | React 19、TypeScript、Vite 8、React Router、Zustand |
| 关系数据库 | 开发环境 SQLite；支持 PostgreSQL/AsyncPG |
| ORM | SQLAlchemy Async |
| 缓存/限流 | Redis，默认 `localhost:6379` |
| 向量数据库 | Qdrant，默认 `http://localhost:6333` |
| Chat | `openai.AsyncOpenAI` 调用 OpenAI-compatible API |
| Embedding | OpenAI-compatible API 或 Sentence Transformers BGE |
| 编排 | LangGraph |

RAG 流程：

```text
上传文件 → 解析 → Chunk → Embedding → Qdrant upsert
用户问题 → query embedding → Qdrant 检索 → SQL Chunk → Prompt → Chat Model
```

向量链路失败、Qdrant 无结果或 Embedding 失败时，聊天流程回退到 SQL 关键词检索。

## 项目结构

```text
AgentForge-main/
├─ backend/
│  ├─ api/routes/              # FastAPI 路由
│  ├─ core/                    # 配置、数据库、安全、Redis 限流
│  ├─ models/                  # SQLAlchemy ORM 和 Pydantic Schema
│  ├─ services/                # Agent、模型、知识库、LangGraph 服务
│  │  ├─ embedding/            # Provider 抽象、OpenAI-compatible、BGE
│  │  ├─ vector_store/          # Vector Store 抽象和 Qdrant
│  │  ├─ knowledge_parser.py   # 文档解析和切片
│  │  ├─ knowledge_service.py  # 知识库和关键词检索
│  │  ├─ knowledge_ingestion_service.py # Embedding/Qdrant 入库
│  │  ├─ rag_retrieval_service.py       # query embedding/向量检索
│  │  └─ langgraph_execution_strategy.py # 执行与 Prompt 注入
│  ├─ config.yaml              # 默认 YAML 配置
│  └─ main.py                  # 后端入口
├─ frontend/src/               # React 页面、业务模块、API Client
├─ scripts/                    # Windows/Shell 启动和环境脚本
├─ tests/unit/                 # 单元测试
├─ tests/integration/          # 集成测试
├─ docs/                       # 设计和测试文档
├─ requirements.txt
├─ backend/requirements.txt
└─ agentforge_preview.db       # 本地开发 SQLite
```

## 环境要求

- Python `>= 3.10`，项目当前启动使用 Python 3.12
- Node.js，当前环境 `v24.14.0`
- npm，当前环境 `11.9.0`
- Redis 或 Memurai，监听 `localhost:6379`
- Qdrant，监听 `localhost:6333`
- 首次使用本地 BGE 需要下载模型权重

当前开发阶段推荐使用本机进程，不使用 Docker 启动后端或前端；Qdrant 需单独运行或连接已有服务。

## Windows 本地部署

### 1. 克隆项目

```powershell
git clone <your-repository-url>
cd AgentForge-main
```

### 2. 创建虚拟环境

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. 安装依赖

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd install --prefix frontend
```

Python 依赖包括 FastAPI、SQLAlchemy、OpenAI、LangGraph、Qdrant、Sentence Transformers、PyTorch、PDF/DOCX 解析和测试工具。

### 4. 配置 `.env`

在项目根目录创建 `.env`，不要提交真实密钥：

```env
ENV=dev
DB_URL=sqlite+aiosqlite:///./agentforge_preview.db
REDIS_URL=redis://localhost:6379/1

OPENROUTER_API_KEY=your-chat-api-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openai/gpt-4o-mini

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=agentforge_knowledge

AUTH_DEV_BYPASS_ENABLED=false
AGENT_CONFIG_SECRET=replace-with-a-long-random-secret
```

配置优先级为：进程环境变量 > `.env` > `backend/config.yaml` > 代码默认值。

### 5. 启动 Redis、Qdrant 和应用

确认 Redis/Memurai 在 `localhost:6379`，可执行 `redis-cli ping` 验证。然后运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev_up.ps1
```

应用启动时自动执行 SQLAlchemy `create_all` 和当前兼容字段迁移，开发数据库默认为根目录 `agentforge_preview.db`。

## 启动命令

推荐：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev_up.ps1
```

后端：

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

后端地址：`http://127.0.0.1:8000`；健康检查：`http://127.0.0.1:8000/health`。

前端：

```powershell
npm.cmd run dev --prefix frontend -- --port 5276 --strictPort
```

前端地址：`http://127.0.0.1:5276`。

启动日志在 `.tmp/dev_up/<timestamp>/`，包括 `backend.log`、`backend.error.log`、`frontend.log` 和 `frontend.error.log`。启动脚本不会自动停止已占用的 8000/5276 端口。

## 配置说明

### 基础、数据库和 Redis

| 变量 | 作用 |
| --- | --- |
| `ENV` | 运行环境，开发环境为 `dev` |
| `APP_NAME` | 服务名称 |
| `LOG_LEVEL` | 日志级别 |
| `CORS_ALLOWED_ORIGINS` | 允许的前端来源 |
| `DB_URL` | SQLAlchemy 异步数据库连接串 |
| `REDIS_URL` | Redis 连接串 |
| `JWT_SECRET` | JWT 密钥 |
| `AGENT_CONFIG_SECRET` | Agent API Key 加密密钥 |

### Chat 模型

代码实际读取的默认变量为：

| 变量 | 作用 |
| --- | --- |
| `MODEL_API_KEY` | 通用 Chat API Key 备用值 |
| `MODEL_BASE_URL` | 通用 Chat Base URL |
| `OPENROUTER_API_KEY` | 默认 Chat API Key |
| `OPENROUTER_BASE_URL` | 默认 Chat Base URL |
| `OPENROUTER_MODEL` | 默认 Chat 模型名 |
| `VITE_API_BASE_URL` | 前端 API 地址，开发模式默认直连 8000 |
| `VITE_AUTH_DEV_BYPASS` | 前端开发认证绕过开关，默认关闭 |

Agent 也可以保存自己的 Chat Provider 地址、模型名和 API Key，因此可接 DeepSeek、OpenAI 及其他 OpenAI-compatible 服务。当前代码没有单独实现 `OPENAI_API_KEY` 或 `DEEPSEEK_API_KEY` 环境变量。

### Qdrant

| 变量 | 默认值 | 作用 |
| --- | --- | --- |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant 地址 |
| `QDRANT_API_KEY` | 空 | Qdrant 鉴权 Key，可选 |
| `QDRANT_COLLECTION` | `agentforge_knowledge` | Collection 名称 |

### Agent Embedding

配置保存于现有 `Agent.config.embedding`，不使用独立密钥存储。

本地 BGE：

```json
{"embedding":{"provider":"bge_local","model":"BAAI/bge-large-zh-v1.5"}}
```

OpenAI-compatible：

```json
{"embedding":{"provider":"openai_compatible","base_url":"https://api.openai.com/v1","model":"text-embedding-3-small","api_key_encrypted":"v1:..."}}
```

BGE 不需要 Base URL 或 API Key，`BAAI/bge-large-zh-v1.5` 向量维度为 1024。后端使用 `AGENT_CONFIG_SECRET` 加密远程 API Key。

## API 接口概览

开发环境路由直接挂载在根路径，不自动添加 `/api/v1` 前缀。大多数业务接口需要认证。

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `GET` | `/health` | 健康检查 |
| `POST` | `/auth/register/start` | 注册开始 |
| `POST` | `/auth/register/verify` | 注册验证 |
| `POST` | `/auth/register/complete` | 完成注册 |
| `POST` | `/auth/login` | 登录 |
| `POST` | `/auth/refresh` | 刷新 Token |
| `GET` | `/auth/session` | 当前会话 |
| `GET/POST` | `/agents` | Agent 列表/创建 |
| `GET/PATCH/DELETE` | `/agents/{id}` | Agent 详情/更新/归档 |
| `POST` | `/agents/{agent_id}/execute` | 执行 Agent |
| `GET/POST` | `/agents/{agent_id}/knowledge` | 知识库列表/手动创建 |
| `POST` | `/agents/{agent_id}/knowledge/upload` | 上传 PDF/DOCX/TXT 并向量化 |
| `POST` | `/agents/{agent_id}/knowledge/search` | 知识库搜索测试 |
| `DELETE` | `/agents/{agent_id}/knowledge/{document_id}` | 删除文档 |
| `GET/POST` | `/executions/{execution_id}` | 读取/停止执行记录 |
| `GET` | `/public/agents` | 公开 Agent 列表 |
| `POST` | `/public/agents/{slug}/execute` | 公开 Agent 执行 |

完整请求/响应以 `backend/models/schemas.py` 和各路由文件为准。

## 知识库与 RAG 代码位置

- 上传与解析：`backend/api/routes/knowledge.py`、`backend/services/knowledge_service.py`、`backend/services/knowledge_parser.py`
- 向量入库：`backend/services/knowledge_ingestion_service.py`、`backend/services/embedding/`、`backend/services/vector_store/`
- 查询向量化：`backend/services/rag_retrieval_service.py`、`backend/services/embedding/factory.py`
- Qdrant 检索：`backend/services/vector_store/qdrant_store.py`
- LangGraph 接入：`backend/services/langgraph_execution_strategy.py`
- Chat 调用：`backend/services/model_gateway.py`

上传成功后，Document 和 Chunk 状态为 `completed`，Qdrant 使用稳定 Chunk ID 作为 Point ID。聊天先进行向量检索，再按 `chunk_id` 查询 SQL 内容并注入现有 Prompt；向量链路失败时回退关键词检索。

## 常见问题排查

### Redis 连接失败

确认 Redis/Memurai 监听 `localhost:6379`，执行 `redis-cli ping`，并检查 `REDIS_URL`。

### API Key 错误

检查 Chat/Embedding Base URL、模型名和 API Key。Embedding Base URL 必须是纯 URL，例如 `https://api.openai.com/v1`，不能包含 `POST` 或 `/embeddings`。本地 BGE 不需要 API Key。

### 前端无法访问后端

确认 `http://127.0.0.1:8000/health` 返回 200、开发前端使用 5276，且 CORS 包含 `http://127.0.0.1:5276`。

### Qdrant 连接失败

```powershell
Invoke-WebRequest http://127.0.0.1:6333/collections
```

确认 Qdrant 地址、API Key、Collection 正确；模型维度必须和 Collection 维度一致。

### 知识库无法检索

检查 `knowledge_documents.embedding_status`、`knowledge_chunks.embedding_status`、Qdrant Collection 和 points，并确认 Agent 的 Embedding 模型与入库时一致。向量和关键词都无结果时，不会向 Chat 注入知识上下文。

### Embedding 失败

本地 BGE 需要 `sentence-transformers`、`torch`、模型权重和足够磁盘空间。远程 Provider 需要合法 URL、API Key 和模型名。失败文档会保留，原因写入 `embedding_error`。

## 开发说明

新增 Agent 配置时复用 `Agent.config`、`backend/services/agent_service.py` 和现有 API Key 加密逻辑。新增工具应遵循 `backend/core/tool_runtime.py`、`backend/core/tools.py` 的权限、风险和日志约定。

新增 Embedding Provider 需要实现：

```python
async def embed_documents(texts): ...
async def embed_query(text): ...
async def validate(): ...
```

并在 `backend/services/embedding/factory.py` 注册，不改变 Qdrant、RAG 和 Chat 上层接口。

测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest tests/unit/test_knowledge_parser.py tests/unit/test_knowledge_retrieval_ranker.py -q
npm.cmd run build --prefix frontend
```

不要提交 `.env`、真实 API Key、生产数据库备份或模型缓存。生产数据库字段变更前应先备份。
