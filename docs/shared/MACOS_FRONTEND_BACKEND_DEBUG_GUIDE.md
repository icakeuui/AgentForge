# AgentForge macOS 前后端联调指南

## 1. 适用范围

本文档用于 `AgentForge-qshuai` 项目在 macOS 环境下进行本机前后端联调。

当前联调/预览方式为：

- 默认预览模式使用 SQLite 文件库
- Redis 仍作为运行时计数与限流依赖
- 本机直接启动 FastAPI 后端
- 本机直接启动 Vite 前端
- 使用统一脚本聚合日志

不依赖 Docker。

## 2. 联调目标

联调完成后，应满足以下目标：

- 前端可访问 `http://localhost:5173`
- 后端可访问 `http://localhost:8000/docs`
- 默认预览库为本地 SQLite 文件
- Redis 监听 `6379`
- 前后端可以通过本地环境变量正常通信

## 3. 目录与入口

本次联调主要依赖以下文件：

- 启动脚本：`scripts/start_mac_dev.sh`
- 测试环境变量：`.env.test`
- 数据库初始化脚本：`tests/create_db.py`
- 后端入口：`backend/main.py`
- 前端入口：`frontend/package.json`

## 4. 环境要求

### 4.1 操作系统

- macOS

### 4.2 必备软件

请确保本机已安装以下工具：

- Python 3
- Node.js / npm
- Redis
- PostgreSQL（仅 PostgreSQL 模式需要）

可通过以下命令检查：

```bash
python3 --version
npm --version
redis-server --version
psql --version
```

## 5. 推荐安装方式

推荐使用 Homebrew 安装本机依赖。

### 5.1 安装 Homebrew

如未安装，可参考 [Homebrew 官网](https://brew.sh/)。

### 5.2 安装 PostgreSQL

```bash
brew install postgresql@16
```

安装完成后，可以手动启动：

```bash
brew services start postgresql@16
```

### 5.3 安装 Redis

```bash
brew install redis
```

安装完成后，可以手动启动：

```bash
brew services start redis
```

### 5.4 安装 Python 依赖

建议在项目根目录创建虚拟环境后安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 5.5 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

## 6. 环境变量说明

脚本默认优先加载项目根目录下的 `.env.test`。

当前关键变量如下：

```env
MODEL_API_KEY=test_key
DB_URL=postgresql+asyncpg://user:password@localhost:5432/agentforge_test
REDIS_URL=redis://localhost:6379/1
ENV=test
APP_NAME=AgentForgeTest
LOG_LEVEL=DEBUG
CONFIG_PATH=backend/config.yaml
```

说明：

- `DB_URL` 在 `.env.test` 中仍保留 PostgreSQL 测试连接
- 启动脚本默认会在预览模式下把 `DB_URL` 覆盖为本机 SQLite 预览库
- `REDIS_URL` 指向本机 Redis 的 `6379`
- 如需切回 PostgreSQL，可执行：

```bash
AGENTFORGE_DB_MODE=postgres ./scripts/start_mac_dev.sh
```

## 7. 一键联调方式

### 7.1 推荐命令

在项目根目录执行：

```bash
./scripts/start_mac_dev.sh
```

### 7.2 脚本启动流程

脚本会依次执行以下动作：

1. 校验当前目录是否为项目根目录
2. 检查 `python3` 或 `python`
3. 检查 `npm`
4. 加载 `.env.test`
5. 清理旧的 `8000` 和 `5173` 端口占用
6. 根据 `AGENTFORGE_DB_MODE` 选择数据库模式
7. 默认预览模式下自动切到 SQLite 预览库
8. PostgreSQL 模式下自动尝试拉起数据库并确保测试库存在
9. 自动检查并尝试启动 Redis
10. 启动 FastAPI 后端
11. 启动前端 Vite 服务
12. 在当前终端聚合输出数据库、Redis、后端、前端日志

### 7.3 启动成功标志

启动成功后，你应看到类似输出：

```bash
✅ 服务启动完毕！
🌐 前端访问地址: http://localhost:5173
🔧 后端 API 地址: http://localhost:8000/docs
```

## 8. 手动联调方式

如果你不想使用一键脚本，也可以手动分别启动依赖和服务。

### 8.1 启动 PostgreSQL

```bash
brew services start postgresql@16
```

### 8.2 启动 Redis

```bash
brew services start redis
```

### 8.3 创建测试数据库

在项目根目录执行：

```bash
python3 tests/create_db.py
```

### 8.4 启动后端

在项目根目录执行：

```bash
export PYTHONPATH="$(pwd)"
set -a
source .env.test
set +a
python3 -m uvicorn backend.main:app --reload --port 8000
```

### 8.5 启动前端

另开一个终端，执行：

```bash
cd frontend
npm run dev
```

### 8.6 使用 SQLite 预览库手动启动

如果你希望手动走“预览模式”，可在项目根目录执行：

```bash
export PYTHONPATH="$(pwd)"
export DB_URL="sqlite+aiosqlite:///$(pwd)/agentforge_preview.db"
export REDIS_URL="redis://localhost:6379/1"
set -a
source .env.test
set +a
export DB_URL="sqlite+aiosqlite:///$(pwd)/agentforge_preview.db"
python3 -m uvicorn backend.main:app --reload --port 8000
```

## 9. 日志说明

脚本运行后会自动在项目根目录创建 `logs/` 目录。

主要日志文件如下：

- `logs/database.log`
- `logs/redis.log`
- `logs/backend.log`
- `logs/frontend.log`

查看指定日志：

```bash
tail -f logs/backend.log
tail -f logs/frontend.log
tail -f logs/database.log
tail -f logs/redis.log
```

## 10. 停止方式

### 10.1 停止一键联调

如果你是通过 `./scripts/start_mac_dev.sh` 启动的，在当前日志窗口按：

```bash
Ctrl + C
```

脚本会自动：

- 停止当前脚本拉起的前后端进程
- 清理 `8000` 和 `5173` 端口占用

注意：

- 脚本不会主动关闭 PostgreSQL
- 脚本不会主动关闭 Redis

这是为了避免误伤你机器上的其他本地开发任务

### 10.2 手动停止 PostgreSQL

```bash
brew services stop postgresql@16
```

### 10.3 手动停止 Redis

```bash
brew services stop redis
```

## 11. 常见问题排查

### 11.1 提示未检测到 PostgreSQL

错误示例：

```bash
❌ 错误: 未检测到已安装的 PostgreSQL，本机无法自动拉起数据库。
```

处理方式：

```bash
brew install postgresql@16
brew services start postgresql@16
```

如果你只是本机预览，不想装 PostgreSQL，可直接使用默认 SQLite 模式：

```bash
./scripts/start_mac_dev.sh
```

### 11.2 提示本地 PostgreSQL 未运行

错误示例：

```bash
❌ 错误: 本地 PostgreSQL 未运行，请先启动对应服务 (端口: 5432)
```

处理方式：

```bash
brew services start postgresql@16
```

验证：

```bash
lsof -i :5432
```

### 11.3 提示本地 Redis 未运行

错误示例：

```bash
❌ 错误: 本地 Redis 未运行，请先启动对应服务 (端口: 6379)
```

脚本会优先尝试自动启动 Redis；如果自动启动失败，再手动执行：

```bash
brew services start redis
```

验证：

```bash
lsof -i :6379
```

### 11.4 后端启动失败

排查顺序：

1. 检查 Python 依赖是否已安装
2. 检查 `.env.test` 是否存在
3. 检查当前数据库模式是否正确
4. PostgreSQL 模式下检查数据库是否能连接
5. 检查 Redis 是否可访问
6. 查看 `logs/backend.log`

建议命令：

```bash
cat logs/backend.log
```

### 11.5 前端启动失败

排查顺序：

1. 检查 `frontend/node_modules` 是否已安装
2. 检查 `npm` 是否可用
3. 检查 Dev Token 生成是否成功
4. 查看 `logs/frontend.log`

建议命令：

```bash
cat logs/frontend.log
```

### 11.6 端口被占用

查看占用：

```bash
lsof -i :8000
lsof -i :5173
```

脚本已内置自动清理逻辑，但如果需要手动处理，可执行：

```bash
kill -9 $(lsof -t -i :8000)
kill -9 $(lsof -t -i :5173)
```

### 11.7 数据库不存在

可手动创建：

```bash
python3 tests/create_db.py
```

仅适用于 PostgreSQL 模式。SQLite 预览模式下，数据库文件会在启动时自动创建。

### 11.8 脚本必须在哪个目录执行

必须在项目根目录执行：

```bash
/Users/laosun/Documents/personal_projects/AgentForge-qshuai
```

否则脚本会因为找不到 `backend/main.py` 而退出。

## 12. 数据库类型与格式说明

### 12.1 正式设计数据库

项目整体架构设计数据库是：

- 主持久化数据库：PostgreSQL
- 运行时计数与限流：Redis

依据：

- [AGENTFORGE_BACKEND_ARCHITECTURE_SPEC.md](file:///Users/laosun/Documents/personal_projects/AgentForge-qshuai/docs/backend/AGENTFORGE_BACKEND_ARCHITECTURE_SPEC.md#L1-L18)
- [PHASE_STATUS.md](file:///Users/laosun/Documents/personal_projects/AgentForge-qshuai/docs/shared/PHASE_STATUS.md#L167-L176)

连接格式：

- PostgreSQL: `postgresql+asyncpg://<user>:<password>@<host>:<port>/<db_name>`
- Redis: `redis://<host>:<port>/<db_index>`

### 12.2 当前预览数据库

当前预览启动明确使用：

- SQLite 预览库
- Redis 仍保留

依据：

- [plugin-marketplace-api.md](file:///Users/laosun/Documents/personal_projects/AgentForge-qshuai/docs/backend/plugin-marketplace-api.md#L9-L14)
- [plugin-marketplace-api.md](file:///Users/laosun/Documents/personal_projects/AgentForge-qshuai/docs/backend/plugin-marketplace-api.md#L239-L243)

连接格式：

- SQLite: `sqlite+aiosqlite:///<absolute_path_to_db_file>`
- 预览脚本默认值：`sqlite+aiosqlite:///$(pwd)/agentforge_preview.db`

### 12.3 前期测试数据库

前期测试分两类：

- 标准集成/验收测试环境：PostgreSQL + Redis
- `plugin_marketplace` 单元测试与预览验证：SQLite 文件库

依据：

- [PHASE_STATUS.md](file:///Users/laosun/Documents/personal_projects/AgentForge-qshuai/docs/shared/PHASE_STATUS.md#L167-L176)
- [docker-compose.test.yml](file:///Users/laosun/Documents/personal_projects/AgentForge-qshuai/docker-compose.test.yml)
- [plugin_marketplace.py tests](file:///Users/laosun/Documents/personal_projects/AgentForge-qshuai/tests/unit/test_plugin_marketplace.py)

### 12.4 当前脚本策略

`scripts/start_mac_dev.sh` 当前默认策略为：

- 默认模式：`SQLite + Redis`
- 显式模式：`AGENTFORGE_DB_MODE=postgres`

这样能同时满足：

- 与“当前预览启动使用 SQLite”的文档保持一致
- 与“正式环境/标准测试环境使用 PostgreSQL + Redis”的设计保持兼容

## 13. 联调完成后的快速检查

推荐按以下顺序验证：

1. 打开 `http://localhost:5173`
2. 打开 `http://localhost:8000/docs`
3. 检查前端页面是否可加载
4. 检查后端 Swagger 是否可访问
5. 检查前端调用接口是否返回正常
6. 检查日志中是否有数据库连接错误、Redis 错误或鉴权错误

## 14. 推荐联调顺序

推荐采用以下固定顺序：

1. 先确认当前使用的是 SQLite 还是 PostgreSQL 模式
2. SQLite 模式下检查 Redis 可用
3. PostgreSQL 模式下检查 PostgreSQL 和 Redis 都可用
4. 运行 `./scripts/start_mac_dev.sh`
5. 优先检查 `backend.log`
6. 再检查 `frontend.log`

这样可以最快定位联调失败点。

## 15. 当前脚本能力边界

当前脚本已支持：

- 自动清理旧前后端进程
- 自动加载 `.env.test`
- 默认切换到 SQLite 预览库
- PostgreSQL 模式下自动尝试启动 PostgreSQL
- PostgreSQL 模式下自动确保测试数据库存在
- 自动尝试启动 Redis
- 自动拉起前后端
- 自动聚合日志

当前脚本未处理：

- 自动安装 PostgreSQL
- 自动安装 Redis
- 自动停止 PostgreSQL
- 自动停止 Redis

## 16. 建议后续增强

后续可继续补充以下能力：

- 增加独立 `stop` 脚本
- 增加环境检测脚本
- 增加一键健康检查脚本
- 增加 SQLite / PostgreSQL 模式切换提示
- 在 README 中增加联调入口链接
