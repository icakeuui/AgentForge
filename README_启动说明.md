# AgentForge 项目启动说明（Windows）

> 适用对象：第一次拿到内部仓库或压缩包的同学。以下命令在项目根目录执行，除非特别注明。项目路径在不同电脑上不同，请先进入自己的 `AgentForge-main` 目录。

## 已配置环境下最快启动

1. 打开 Docker Desktop，执行 `docker info`，确认 Docker Engine 可用。
2. 执行 `docker ps -a`，找到本机已有的 Qdrant 容器；未运行时执行 `docker start <容器名>`，再请求 `http://127.0.0.1:6333/collections`。当前这台机器的容器名是 `unruffled_bhaskara`，其他电脑不要直接照搬。
3. 确认 Redis/Memurai 在 `6379`：执行 `redis-cli ping`，或使用本机 Memurai CLI；成功为 `PONG`。
4. 确认 `8000`、`5276` 没有旧实例占用，在项目根目录执行 `powershell -ExecutionPolicy Bypass -File scripts\dev_up.ps1`。
5. 浏览器打开 `http://127.0.0.1:5276`，并请求 `http://127.0.0.1:8000/health`。两者可访问才算应用启动完成。脚本不会启动 Qdrant。

## 1. 项目简介

AgentForge 是智能体搭建辅助实践平台，支持注册登录和邮箱验证码、智能体创建、System Prompt 与逻辑配置、OpenAI Compatible 模型连接、Embedding 与本地 BGE、知识库/RAG、工具和智能体运行。界面还提供对话预览、附件与语音输入、智能体广场、公开智能体对话及学习中心。

### 运行架构

| 组成 | 当前实现和职责 |
| --- | --- |
| 前端 | React + Vite + TypeScript；页面、用户交互、智能体配置与对话界面 |
| 后端 | FastAPI；认证、Agent 管理、模型调用、RAG、文件处理和公开智能体接口 |
| Redis/Memurai | 后端限流和团队令牌用量状态；团队配额上限来自数据库，用量计数由 Redis 保存 |
| Qdrant | 存放知识库的向量及检索所需的点数据 |
| SQLite | 本地文件数据库，保存用户、认证、智能体、知识库文档与切片等业务数据；具体表由后端 ORM 初始化 |

## 2. 与运行有关的目录

| 路径 | 用途 |
| --- | --- |
| `frontend/` | React/Vite 前端；`public/` 为前端静态资源，`node_modules/` 为本地依赖 |
| `backend/` | FastAPI 入口、接口、服务及 `config.yaml` 默认配置 |
| `scripts/` | `dev_up.ps1` 启动脚本、`reset_env.ps1` 重建 Python 环境脚本；启动时需要关注，勿误运行重建脚本 |
| `tests/` | 单元和集成测试；正常启动不需要执行，不要用测试命令处理生产数据 |
| `agentforge_preview.db` | 当前本地开发使用的持久化 SQLite 文件 |
| `.tmp/dev_up/` | 一键启动生成的日志和进程号文件；可用于排错，不是永久知识库 |
| `.tmp/public_conversations/` | 公开会话临时附件提取文本，按有效期清理；不是创建者知识库，也不是永久存储 |
| `uploads/` | 后端提供的上传文件目录，对应 `/uploads` 静态路径；可能含用户文件，不要随意删除 |
| `backend/config.yaml`、根目录 `.env` | 默认配置和本机覆盖配置；启动前应检查；`.env` 可能含敏感信息 |

**删除原则：**不要删除 `agentforge_preview.db`、`uploads/`、现有 Qdrant 容器或不明用途的数据目录。`.tmp/` 虽被 Git 忽略，但其中可能有尚未过期的公开会话附件和启动日志，运行中不要清空。

## 3. 运行环境

- Windows，使用 PowerShell 执行项目脚本。
- Python **3.10 或以上**；当前本机项目环境为 **3.12.6**。
- Node.js 和 npm；当前本机分别为 **v24.14.0**、**11.9.0**。项目没有声明强制的 Node/npm 最低版本。
- Redis 或 Memurai，监听本机 `6379`；当前本机使用 Memurai。
- Docker Desktop 与 Qdrant：当前本机的 Qdrant 以 Docker 容器运行，将容器 `6333` 映射到本机 `6333`。仓库没有 Qdrant 专用的 Compose 文件或统一创建脚本。

先用以下命令核对环境；版本与本机不完全相同不代表一定不能运行，但 Python 必须满足项目脚本的最低要求：

```powershell
py --version
node -v
npm -v
docker info
```

## 4. 第一次运行前准备

在 PowerShell 中进入项目根目录，再执行以下步骤。

如果收到 ZIP，先解压并进入包含 `frontend/`、`backend/`、`scripts/` 的目录；Git 仓库同理。尽量使用稳定且便于复制的路径。当前项目路径包含中文用户名且能够运行，因此不要求必须改成英文路径。确认根目录后检查 `.env` 是否已由团队提供；仓库内的 `backend/.env.example` 是模板，**真正被后端自动读取的是项目根目录 `.env`**。不要把模板中的示例账号或占位值当作实际配置。随后按“依赖 → Docker/Qdrant → Redis → 前后端”的顺序操作。

### 后端依赖

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

项目使用根目录 `.venv`，不是 Conda。ZIP 中若已含可用 `.venv`，先执行 `.\.venv\Scripts\python.exe --version` 检查；虚拟环境通常依赖本机路径，跨电脑复制后不能运行时再新建。也可用 `.\.venv\Scripts\Activate.ps1` 激活，但后文使用完整 Python 路径，无需激活。没有 Python 3.12 时，可用已安装的 Python 3.10 以上版本创建。依赖清单为根目录 `requirements.txt`；成功后可验证：

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import fastapi, sqlalchemy, redis, qdrant_client; print('后端关键依赖可导入')"
```

`scripts\reset_env.ps1` 也能重建环境，但会**删除现有 `.venv`**，不要把它当成日常启动命令。

### 前端依赖

```powershell
npm.cmd install --prefix frontend
```

`node_modules/` 不需要放进 ZIP；已有且可用时可跳过安装。安装成功后可执行 `npm.cmd run build --prefix frontend` 检查 TypeScript 与打包。该命令只验证构建，不启动服务；失败时先看 npm 输出。正常开发仍使用 Vite 的 `dev` 命令。

### Redis / Memurai

先启动本机 Redis 或 Memurai 服务，并确认 `127.0.0.1:6379` 可连接。当前机器使用已安装的 Memurai 服务；启动脚本在 Redis 未就绪时会尝试启动可在 PATH 中找到的 Redis/Memurai 程序，但不能代替首次安装。

```powershell
& 'C:\Program Files\Memurai\memurai-cli.exe' ping
```

当前机器正常返回 `PONG`。若安装路径不同，使用实际路径或 `redis-cli ping`。

也可执行 `netstat -ano | findstr :6379` 看监听端口。Redis 没运行时，限流和令牌用量检查可能失败，相关请求可能报错；先检查服务，再检查 `REDIS_URL`。

### Docker / Qdrant

启动 Docker Desktop，然后启动**已有的 Qdrant 容器**并检查接口。当前机器容器名为 `unruffled_bhaskara`，其他机器应先用 `docker ps -a` 找到自己的 Qdrant 容器名。

```powershell
docker ps -a
docker start unruffled_bhaskara
Invoke-WebRequest http://127.0.0.1:6333/collections
```

容器已运行时不用重复执行 `docker start`。新机器若没有 Qdrant 容器，需要先按团队现有部署方式创建一个映射 `6333:6333` 的 Qdrant 实例；仓库没有可直接复制的首次创建命令。**当前机器的 Qdrant 容器没有挂载宿主机目录或 Docker 卷**，数据仅保存在该容器的可写层；删除或重建容器会丢失其中的数据。需要长期保存向量数据时，应先确定团队的持久化部署方案。

若 `docker info` 报无法连接 Engine，先等待 Docker Desktop 显示运行状态；若 `/collections` 不通，用 `docker ps` 检查容器和端口映射，用 `docker logs <容器名> --tail 100` 查看 Qdrant 日志。`docker-compose.test.yml` 中只有测试数据库与测试 Redis，不能用它来启动 Qdrant。

## 5. 启动前检查配置

后端配置优先级为：**进程环境变量 > 项目根目录 `.env` > `backend/config.yaml` > 代码默认值**。不要把真实密钥写进说明文档。以下是实际使用的变量名和用途；按需要写入本机 `.env`，不要照抄空值覆盖有效配置。

```dotenv
# Chat 模型；OPENROUTER_* 为默认模型接入配置，MODEL_* 为备用配置
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=
OPENROUTER_MODEL=
MODEL_API_KEY=
MODEL_BASE_URL=

# 邮件验证码与通知；SMTP_PASSWORD 应填写邮箱服务提供的授权码
SMTP_HOST=
SMTP_PORT=
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_FROM_NAME=
SMTP_USE_TLS=
SMTP_USE_SSL=
EMAIL_DELIVERY_MODE=

# 数据与服务连接
DB_URL=
REDIS_URL=
QDRANT_URL=
QDRANT_API_KEY=
QDRANT_COLLECTION=

# 认证及智能体密钥加密
JWT_SECRET=
AGENT_CONFIG_SECRET=
AUTH_DEV_BYPASS_ENABLED=
```

未覆盖时，本地开发默认使用项目根目录的 `agentforge_preview.db`、`redis://localhost:6379/0`、`http://localhost:6333`。这是**文件型 SQLite 持久化数据库**，不是内存数据库。前端可用 `VITE_API_BASE_URL` 指定后端地址；本地默认连接 `8000`。正常使用时不要开启 `AUTH_DEV_BYPASS_ENABLED` 或前端 `VITE_AUTH_DEV_BYPASS`。

**配置检查顺序：**先看根目录 `.env` 是否存在，再核对模型 Base URL、Key、模型名；SMTP 主机、端口、用户名、授权码、发件地址及 TLS/SSL；`DB_URL` 的文件路径；`REDIS_URL`；`QDRANT_URL` 和 `QDRANT_COLLECTION`。不用把真实值贴到聊天、截图或公开 Issue。运行 `dev_up.ps1` 时还要留意脚本会覆盖部分变量，见第 6 节。正常运行不要使用 `:memory:` SQLite、测试数据库或测试模式。

### 邮箱验证码配置

注册和找回密码使用后端邮件流程。SMTP 配置由上述优先级加载；`EMAIL_DELIVERY_MODE=smtp` 时需要可用的 SMTP 服务。网站即使能打开，SMTP 缺失或配置错误仍会使验证码发送失败。请核对 `SMTP_HOST`、`SMTP_PORT`、`SMTP_USERNAME`、`SMTP_PASSWORD`、`SMTP_FROM_EMAIL`、`SMTP_USE_TLS`、`SMTP_USE_SSL`；`SMTP_PASSWORD` 通常是邮箱服务商签发的 SMTP 授权码，不一定是网页登录密码。QQ/163 等邮箱应按各自后台要求开通 SMTP 并取得授权码；端口与加密方式必须配套，SSL 与 STARTTLS 不要同时开启。操作后在注册页发一次验证码，以后端日志和实际收件箱为准，不要只凭页面能打开判断邮箱正常。

## 6. 推荐启动方式

确认 Redis/Memurai 和 Qdrant 已启动、`.venv` 已创建，并在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev_up.ps1
```

这是项目 README 推荐的一键启动方式。脚本会检查 `8000`、`5276` 端口，检查 Redis，安装/更新 Python 依赖，在缺少前端 `node_modules` 时安装 npm 依赖，然后启动 FastAPI 和 Vite，并持续监看进程。它**不会启动 Qdrant**，也**不会自动停止占用端口的旧进程**。

注意脚本的实际配置行为：它会加载 `.env`（以及存在时的 `.env.test`），将 `ENV` 设为 `dev`，将 `DB_URL` 固定为项目根目录的 `agentforge_preview.db`，将 `REDIS_URL` 设为 `redis://localhost:6379/1`。该 SQLite 文件仍是磁盘持久化文件，但 Redis DB 编号与手动启动的默认配置不同。脚本还要求 `OPENROUTER_API_KEY` 或 `MODEL_API_KEY` 已配置。需要严格沿用 `.env` 中自行指定的数据库或 Redis URL 时，使用下面的手动启动方式。

## 7. 手动启动方式

先启动 Redis/Memurai 与 Qdrant（见第 4 节），再从项目根目录打开**两个独立的 PowerShell 窗口**。后端设置 `PYTHONPATH` 后启动：

```powershell
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

另一个窗口启动前端：

```powershell
npm.cmd run dev --prefix frontend -- --port 5276 --strictPort
```

这两条命令对应项目 README 和 `frontend/package.json`。Vite 配置也固定开发端口为 `5276`，并启用 `strictPort`。手动启动时，后端按第 5 节配置优先级读取现有配置；不额外指定数据库地址即可使用项目的文件型 SQLite 默认配置。`docker-compose.test.yml` 只定义测试用 PostgreSQL/Redis，不用于本地正常启动。

## 8. 启动成功后的地址

| 服务 | 地址 |
| --- | --- |
| 前端 | `http://127.0.0.1:5276` |
| 后端 | `http://127.0.0.1:8000`（根路径可能返回 404，表示没有根路由） |
| 健康检查 | `http://127.0.0.1:8000/health` |
| FastAPI 文档 | `http://127.0.0.1:8000/docs` |
| Qdrant | `http://127.0.0.1:6333` |
| Redis/Memurai | `127.0.0.1:6379` |

## 9. 启动后检查

```powershell
Invoke-WebRequest http://127.0.0.1:5276
Invoke-WebRequest http://127.0.0.1:8000/health
Invoke-WebRequest http://127.0.0.1:8000/docs
Invoke-WebRequest http://127.0.0.1:6333/collections
& 'C:\Program Files\Memurai\memurai-cli.exe' ping
```

前四项应返回成功状态，Memurai 应返回 `PONG`。然后在浏览器中检查：前端页面可打开、可注册/登录、邮箱验证码可发送、可进入智能体开发、可正常对话。邮件和对话功能还依赖正确的 SMTP、模型配置及外部服务可用性。

## 10. 常见问题

| 现象 | 常见原因 | 处理方法 |
| --- | --- | --- |
| 前端打不开 / `ERR_CONNECTION_TIMED_OUT` | Vite 未启动或 `5276` 被占用 | 检查前端窗口输出与 `5276` 监听进程；停止旧实例后重启。 |
| 页面提示 `Failed to fetch` | FastAPI 未启动、前端 API 地址或 CORS 不匹配 | 请求 `/health`；检查 `VITE_API_BASE_URL`、后端日志与 `5276` 来源配置。 |
| `401 invalid_api_key` | Chat/Embedding API Key 无效或与服务商不匹配 | 核对对应模型的 Key、Base URL、模型名；不要在日志或聊天中贴出 Key。 |
| `Invalid endpoint URL` | 模型或 Embedding Base URL 格式错误 | 填纯 API 基础 URL，不要填 `POST` 命令或把 `/embeddings` 当基础 URL。 |
| Redis `6379` 未启动 | Redis/Memurai 服务未运行 | 启动服务，执行 `redis-cli ping` 或 Memurai CLI `ping`，核对 `REDIS_URL`。 |
| Qdrant `6333` 未启动 | Docker Desktop 或 Qdrant 容器未运行 | 运行 `docker ps -a`，启动已有容器，再请求 `/collections`。 |
| 邮箱验证码发送失败 | SMTP 服务不可达、授权码或发件地址不正确 | 检查后端日志及 SMTP 变量，使用邮箱服务商提供的授权码。 |
| SMTP 配置问题 | TLS/SSL、端口与邮箱服务商要求不一致 | 核对 `SMTP_HOST`、`SMTP_PORT`、`SMTP_USE_TLS`、`SMTP_USE_SSL`、`SMTP_USERNAME`、`SMTP_FROM_EMAIL`。 |
| BGE 第一次加载较慢 | 首次下载和加载本地模型权重 | 保持网络连接并等待首次加载完成，查看后端日志。 |
| 上传知识库后没有检索到内容 | Embedding 失败、Qdrant 无数据或模型维度不一致 | 检查文档 `embedding_status`/`embedding_error`、Qdrant Collection 和 Agent 的 Embedding 配置。 |
| 端口被旧进程占用 | 已有 Vite/FastAPI 实例仍在运行 | 按第 11 节识别进程并停止旧实例，再启动一次。 |

## 11. 正确关闭和重新启动

手动启动时，在前端和后端各自的 PowerShell 窗口按 `Ctrl+C`，等待进程退出。使用 `dev_up.ps1` 时，在运行脚本的 PowerShell 窗口按 `Ctrl+C`，再检查子进程是否仍占用端口。

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object { $_.LocalPort -in 5276, 8000 } |
  Select-Object LocalPort, OwningProcess
```

如仍有监听进程，先用 `Get-CimInstance Win32_Process -Filter "ProcessId=<PID>"` 核对命令行，确认属于本项目后停止对应进程；不要按端口盲目结束其他程序。端口释放后，只执行一次第 6 节启动脚本，或各执行一次第 7 节前后端命令，避免重复启动多个 Vite/FastAPI 实例。Redis 与 Qdrant 正常运行时无需反复创建或重启。

## 12. 内部使用提醒

`.env` 可能包含 API Key、SMTP 授权码等敏感配置，不要公开上传或提交到公开仓库。内部压缩包若包含真实配置，仅限内部成员使用。`agentforge_preview.db` 和 Qdrant 数据也属于项目运行数据，删除、重建或复制前先确认用途。

## 13. 一键脚本运行时应该看到什么

先完成基础服务检查，再在项目根目录执行第 6 节命令。脚本依次输出 `checking required ports`、Python/Node/npm 版本、`Redis OK`、`starting backend`、`starting frontend`，最后输出 `services up`、日志目录和进程号。前端地址应能打开，后端 `/health` 应返回 200。脚本会一直运行，终端暂时不会返回命令提示符，这是正常的进程监看行为。

脚本已经带 `-ExecutionPolicy Bypass`，只作用于这次 PowerShell 进程，无需永久改系统策略。如果端口已占用，它会报错退出，请先按第 17 节核对旧进程。若启动失败，打开输出中的 `.tmp/dev_up/<时间戳>/`，查看 `backend.error.log`、`frontend.error.log` 和对应标准输出日志。

## 14. 标准启动顺序与手动成功标准

新成员按 **Docker Desktop → Qdrant → Redis/Memurai → FastAPI → Vite → 浏览器** 操作。一键脚本只替代最后的 FastAPI 与 Vite 两步，并会检查 Redis；Qdrant 仍需先启动。

手动后端命令见第 7 节。终端出现 `Uvicorn running on http://0.0.0.0:8000`、`Application startup complete`，再请求 `/health` 得到 200，才算启动成功。`http://127.0.0.1:8000/` 返回 404 仅表示未定义根路由。前端终端出现 Vite 的本地地址 `http://localhost:5276/`，浏览器能打开 `http://127.0.0.1:5276`，才算前端成功。前端报 `ERR_CONNECTION_TIMED_OUT` 时先查 `5276`；页面登录时出现 `Failed to fetch` 时先查后端 `8000` 与 `/health`。

## 15. 首次启动后的功能验证

以下是人工验收流程，不要在正式业务数据中随意创建测试账号或测试知识库；使用团队提供的测试身份和可删除的样例内容。

| 步骤 | 操作 | 成功表现 |
| --- | --- | --- |
| 1 | 打开首页 | 页面资源加载完成，没有空白页 |
| 2 | 打开登录页 | 登录表单可见，浏览器 Network 没有持续连接错误 |
| 3 | 在注册流程请求邮箱验证码 | 页面显示发送结果，测试邮箱收到验证码；失败时检查 SMTP 日志 |
| 4 | 登录 | 进入已登录界面，不反复跳回登录页 |
| 5 | 进入学习中心 | 页面和内容能显示 |
| 6 | 进入智能体开发 | 智能体列表/编辑区域可见 |
| 7 | 打开一个已有智能体 | 配置和预览区能加载；没有现成 Agent 时可用团队允许的样例 |
| 8 | 检查模型配置 | Base URL、模型名等显示合理；无需在文档或截图中暴露 Key |
| 9 | 发送普通消息 | 出现用户消息及模型回复，或得到可定位的模型错误 |
| 10 | 在开发页测试附件 | PDF/DOCX/TXT 可上传并显示附件；注意此处走知识库文档上传 |
| 11 | 测试语音输入 | 授予麦克风权限后，识别文字进入输入框；需要手动点击发送 |
| 12 | 查看知识库 | 文档列表及处理状态能显示 |
| 13 | 用样例文档测试 RAG | 上传后状态为完成，针对文档内容提问能获得相关结果 |
| 14 | 打开智能体广场 | 已发布且可用的智能体可见 |
| 15 | 打开一个公开智能体并对话 | 无需进入创建者开发页即可收到公开对话结果；可另测临时附件 |

这些步骤覆盖前后端及外部模型、SMTP、向量链路；`/health` 成功只说明后端存活，不能代替功能验证。

## 16. 模型连接、本地 BGE 与 RAG

平台使用 OpenAI Compatible 模型服务，项目默认变量采用 `OPENROUTER_*`，也有 `MODEL_*` 备用字段；具体 Agent 可保存自己的模型连接配置。DeepSeek 可作为兼容服务的一种，不是唯一支持的服务。Base URL 应填服务商提供的 API 基础地址，模型名和 Key 必须属于同一服务商。出现 `401 invalid_api_key`，依次核对 API Key、Base URL、模型名；出现 `Invalid endpoint URL`，先检查 URL 是否为纯地址，是否误填 `POST` 或具体的 `/embeddings` 路径。

Embedding 支持 `openai_compatible` 和 `bge_local`。本地 BGE 默认模型是 `BAAI/bge-large-zh-v1.5`，无需远程 Embedding API Key；首次使用可能需要联网下载权重，加载较慢，之后由进程内缓存复用。仓库依赖包含 `sentence-transformers`，实际计算设备取决于本机可用环境，不在此保证 GPU。远程 Embedding 需有效 Base URL、Key、模型名；Agent 配置中的 Key 经后端加密。

知识库排查按这条链路：**上传 PDF/DOCX/TXT → 解析 → 切片 → Embedding → Qdrant upsert → 提问检索**。文件上传成功不等于向量入库成功；查看文档 `embedding_status` 与 `embedding_error`，确认 `6333` 可访问、`QDRANT_COLLECTION` 对应的 Collection 存在、点数据已写入，再检查提问时使用的 Agent Embedding 配置及后端日志。模型维度不一致也会导致向量链路失败。项目在向量检索失败或无结果时可能回退 SQL 关键词检索，因此偶尔有回答不代表 Qdrant 已正常入库。

## 17. 附件与语音输入的实际行为

开发页的对话输入一次最多选择 **1 个附件**，上传走 Agent 的知识库文档接口；这与广场公开对话的临时附件不是一套存储。两边前端都只接受 PDF、DOCX、TXT，单文件上限 **100 MB**。开发页上传后应检查对应知识库文档的处理状态。

公开智能体对话一次最多 **3 个不同附件**，单会话最多 **20 个文件**、累计 **200 MB**。上传后后端只保留解析出的文本，单文件提取文本上限 **2 MB**；原二进制文件不会在该临时附件服务中持久保存。文本和元数据保存在项目根目录 `.tmp/public_conversations/<会话 ID>/`，会话有效期 **24 小时**，过期内容由运行中的后端定期清理。对话时读取附件的前段文本作为上下文，不会自动进入创建者知识库或 Qdrant。公开附件无法解析、超限或过期时，应在页面、后端日志中核对具体错误；不要通过清空 `.tmp/` 来“修复”运行中的会话。

语音输入由浏览器的 `SpeechRecognition` 或 `webkitSpeechRecognition` 实现，语言设为 `zh-CN`。首次使用需要授予麦克风权限；Chrome/Edge 通常可作为支持 Web Speech API 的浏览器进行验证，但以当前浏览器实际支持为准。浏览器不支持时页面会提示；设备、权限或网络错误也会显示对应提示。识别出的文字只进入输入框，**不会自动发送**，可先检查和修改，再按发送按钮。

## 18. SQLite 与运行数据

当前本地正常开发默认数据库是根目录的 `agentforge_preview.db`，文件名含 `preview`，但它是**磁盘上的持久化业务数据库**，不是 Vite 预览模式，也不是临时内存库。后端 `backend/core/config.py` 会把 YAML 中的相对 SQLite 路径规范到项目根目录；启动时 `backend/main.py` 会对 ORM 表执行 `create_all` 并运行兼容字段初始化。已有文件不要删除或用空库替换，否则原账号、Agent、知识库和其他业务记录可能看不到。根目录还可能有测试库或备份库，正常启动不要指向它们，也不要运行会清空数据库的测试/重置命令。

如果登录提示 `Invalid email or password`，先确认账号输入，再检查当前后端 `DB_URL` 是否指向**预期的那份持久文件**，尤其注意进程环境变量和 `dev_up.ps1` 的覆盖行为。不要为了排错随意改密码、复制测试库或删除 SQLite 文件。Redis 负责限流及用量状态，Qdrant 负责向量点，二者不能由 SQLite 文件单独恢复。

## 19. 正确关闭、重新启动与端口占用

手动运行时分别在后端、前端终端按 `Ctrl+C` 并等待退出；使用 `dev_up.ps1` 时先在其终端按 `Ctrl+C`，再检查子进程是否已结束。Redis/Memurai 和 Qdrant 正常运行时不必为重启前后端而停止；只有需要关闭整套本机环境时才按团队方式停止相应服务或 Docker Desktop。关闭 Docker Desktop 会使其容器不可访问；不要删除 Qdrant 容器。

最简重启：检查 `5276` 和 `8000` → 停止属于本项目的旧 Vite/Uvicorn → 确认 Redis `6379` 和 Qdrant `6333` → 重新启动后端 → 重新启动前端 → 请求 `/health` 并打开首页。如果用一键脚本，端口释放后只运行一次脚本即可。

```powershell
netstat -ano | findstr :5276
netstat -ano | findstr :8000
netstat -ano | findstr :6379
netstat -ano | findstr :6333
```

每行末尾为 PID；要识别归属可执行 `Get-CimInstance Win32_Process -Filter 'ProcessId=12345' | Select-Object ProcessId,Name,CommandLine`（把 `12345` 换成实际 PID）。只停止命令行明确指向本项目的旧进程；优先在原终端按 `Ctrl+C`。旧终端不可用时，确认 PID 后才用 `Stop-Process -Id 12345`；若进程有子进程，还需分别检查其占用，避免误结束 Docker、Memurai 或其他项目。

## 20. 常见问题：现象 → 原因 → 检查 → 处理

| 现象 | 常见原因 | 检查 | 处理 |
| --- | --- | --- | --- |
| 前端 `ERR_CONNECTION_TIMED_OUT` | Vite 未启动或端口错误 | `netstat` 查 `5276`，看前端日志 | 释放旧端口，按第 7 节重启 Vite |
| 登录 `Failed to fetch` | 后端未启动、地址/CORS 不对 | 请求 `/health`，看浏览器 Network | 启动后端，核对 `VITE_API_BASE_URL` 与来源地址 |
| `Invalid email or password` | 凭据错误或连错数据库 | 核对账号及后端 `DB_URL` | 使用正确持久数据库；不要重置原库 |
| 验证码发送失败 | SMTP 配置或网络错误 | 看后端日志和收件箱/垃圾箱 | 核对授权码、主机、端口、TLS/SSL、发件地址 |
| `401 invalid_api_key` | 模型凭据不匹配 | 核对对应 Agent 的 Key、Base URL、模型名 | 更新正确凭据，勿公开 Key |
| `Invalid endpoint URL` | Base URL 格式错误 | 看模型/Embedding 基础地址 | 改为纯 API 基础 URL |
| Redis 请求失败 | `6379` 未监听或 URL 不对 | `ping`、`netstat`、`REDIS_URL` | 启动服务并核对数据库编号 |
| Qdrant 请求失败 | Docker/容器未启动或 `6333` 不通 | `docker ps`、请求 `/collections` | 启动已有容器，检查端口映射和日志 |
| 知识库上传后检索不到 | Embedding 或 upsert 失败、Collection 不匹配 | `embedding_status/error`、Qdrant 点、后端日志 | 修正 Embedding 与 Qdrant 配置后重新处理样例文档 |
| BGE 首次很慢 | 下载或加载模型权重 | 看后端日志和网络状态 | 等待首次加载完成，确认依赖与磁盘空间 |
| 麦克风无反应 | 浏览器不支持或无权限 | 浏览器权限、Console、设备状态 | 授权麦克风，换支持 Web Speech API 的浏览器 |
| 附件上传失败 | 格式、大小、数量或会话有效期限制 | 看页面提示、Network 响应、后端日志 | 使用 PDF/DOCX/TXT 并遵守第 17 节限制 |
| 启动时报端口占用 | 旧 Vite/Uvicorn 还在 | `netstat` 和 PID 命令行 | 确认归属后停止旧进程，避免重复启动 |

## 21. 日志与浏览器排错入口

- **一键启动：**脚本输出 `.tmp/dev_up/<时间戳>/`；后端看 `backend.log`、`backend.error.log`，前端看 `frontend.log`、`frontend.error.log`。
- **手动启动：**先看各自 PowerShell 窗口。后端异常优先查看 traceback 与请求状态码；Vite 编译错误会在前端终端显示。
- **浏览器：**按 F12 看 Console 的脚本错误；Network 看请求实际 URL、HTTP 状态和响应体。`Failed to fetch` 优先看请求是否到达 `8000`。
- **Qdrant：**`docker ps` 看容器，`docker logs <容器名> --tail 100` 看服务日志，`/collections` 看接口可用性。
- **Redis/Memurai：**先用 CLI `ping`，再看本机服务状态和 Memurai 自身日志；当前安装目录下有 `memurai-log.txt`，其他机器以实际安装位置为准。

## 22. 内部 ZIP 与安全检查

收到内部 ZIP 后：解压 → 确认根目录 → 查看根目录 `.env` 是否由团队提供 → 安装 Python/npm 依赖 → 打开 Docker Desktop → 启动 Qdrant → 确认 Redis → 执行 `dev_up.ps1` → 打开前端并按第 15 节验证。ZIP 中若含真实内部配置，只能按团队要求在内部传递。

不要公开上传 `.env`、API Key、SMTP 授权码、用户数据库、`.tmp/`、用户上传文件或真实账号数据。分享日志和截图前也要检查是否含凭据或用户内容。
