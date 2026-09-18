# E2E 全栈联调脚本使用说明

本文档说明如何使用 `tests/e2e/start_fullstack_e2e.sh`，实现稳定的前后端联调启动：

- 启动顺序：后端先启动并通过健康检查，再启动前端
- 自动清理：清理旧 PID、旧端口占用、旧 uvicorn/vite 进程
- 自动服务：自动拉起 Redis，自动使用 SQLite（`agentforge_preview.db`）
- 日志合并：前后端日志同屏输出，并带 `[backend]` / `[frontend]` 前缀（底层写入 `.tmp/e2e_fullstack/*.log`）

## 1. 前置条件

- macOS / Linux
- `python3.10+`
- `node` / `npm`
- `redis-server` / `redis-cli`
- 建议在项目根目录存在 `.venv`（脚本会自动尝试激活）

## 2. 启动命令

在项目根目录执行：

```bash
bash ./tests/e2e/start_fullstack_e2e.sh
```

如果你已经给脚本加了执行权限，也可直接执行：

```bash
./tests/e2e/start_fullstack_e2e.sh
```

## 3. 脚本做了什么

1. 清理历史残留：

- 清理 `.tmp/e2e_fullstack` 与 `.tmp/dev_up` 的历史 pid
- 清理端口：`8000`、`5173`、`5174`
- 清理历史 `uvicorn backend.main:app` 和 `vite/npm run dev`

1. 启动依赖服务：

- 检查并启动 Redis（6379）
- 设置 SQLite 数据库 URL：
  `sqlite+aiosqlite:///.../agentforge_preview.db`

1. 启动后端：

- `uvicorn backend.main:app --host 127.0.0.1 --port 8000`
- 轮询 `GET /health`，健康通过后才进入下一步

1. 启动前端：

- 在 `frontend` 目录启动 `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`
- 若不存在 `node_modules`，自动执行 `npm install`
- 脚本会检测 `http://127.0.0.1:5173` 就绪；若失败会直接退出并提示日志路径

1. 合并日志：

- 后端日志统一前缀 `[backend]`
- 前端日志统一前缀 `[frontend]`

## 4. 停止方式

- 前台运行时按 `Ctrl+C`
- 脚本会自动清理它启动的前后端进程与临时管道

## 5. 常见问题

- `redis-cli not found` / `redis-server not found`
  - 需要先安装 Redis 并确保命令在 PATH 中
- `backend failed health check`
  - 查看同屏 `[backend]` 日志定位错误（常见为 Python 版本或依赖问题）
- 前端拒绝连接（`ERR_CONNECTION_REFUSED`）
  - 先看：`.tmp/e2e_fullstack/frontend.log`
  - 该脚本已固定 `127.0.0.1:5173` 且 `strictPort`，不会再自动漂移端口

## 6. 测试示例任务（覆盖 Agent 全能力）

本节用于在联调环境中验证单 Agent 能力闭环。先创建一个基线 Agent，再执行下面任务。

### 6.1 基线 Agent 配置（固定示例）

- Agent Identity
- Name：`coder`（用于工作区与 Agent 列表显示）
- Avatar：`https://example.com/avatar.png`（可选）
- Description：`你是一个严谨的代码助手。先给结论，再给最小可执行步骤。`（必填，执行时注入 prompt 链路）
- Model Connection
- Base URL：`https://api.openai.com/v1`（必填，必须为 OpenAI-compatible endpoint，禁止 localhost/内网地址）
- API Key：填写有效 API Key（必填；已保存 key 不回显，编辑仅支持覆盖更新）
- Model Name：`gpt-4o-mini`（必填）
- Advanced Runtime
- Temperature：`0.7`
- Max Tokens：`1000`（留空表示 provider 默认）
- Capability Flags：`supports_tools = true`（需与模型能力一致）

### 6.2 示例任务 A：纯对话推理能力（不触发工具）

- 输入：
  `请用三句话解释什么是幂等性，并给一个 HTTP API 例子。不要调用任何工具。`
- 预期：
  - 成功返回最终答案；
  - 语义完整、无工具调用；
  - 执行状态结束为成功。

### 6.3 示例任务 B：基础工具调用能力（echo\_tool）

- 输入：
  `请调用 echo_tool，输入 x=41，并返回最终结果。`
- 预期：
  - 至少产生 1 次 tool call；
  - tool\_id 为 `echo_tool`；
  - 观测结果包含 `y=42`；
  - 最终答案正确引用工具结果。

### 6.4 示例任务 C：Sandbox 集成能力（python\_add\_tool）

- 输入：
  `请调用 python_add_tool，输入 x=99，并只返回最终数值。`
- 预期：
  - 至少产生 1 次 tool call；
  - tool\_id 为 `python_add_tool`；
  - 观测结果中数值为 `100`；
  - 执行链路无沙箱错误。

### 6.5 示例任务 D：通用 Python 执行能力（python\_executor）

- 输入：
  `请调用 python_executor 执行以下代码并返回结果：result = {"sum": sum([1,2,3,4,5]), "max": max([1,2,3,4,5])}`
- 预期：
  - 至少产生 1 次 tool call；
  - tool\_id 为 `python_executor`；
  - 观测结果包含 `sum=15`、`max=5`；
  - 最终答案与观测结果一致。

### 6.6 示例任务 E：工具能力开关校验（supports\_tools）

- 操作：
  - 将 `supports_tools` 改为 `false` 后保存；
  - 再执行“示例任务 B”。
- 预期：
  - 系统拒绝工具调用或返回能力不匹配错误；
  - 不应发生“伪成功”；
  - 错误信息可观测（前端提示 + 后端日志可定位）。

### 6.7 验收建议（最小）

- 每个示例任务连续执行 3 次；
- 成功判定：3 次中至少 2 次满足预期；
- 失败时优先检查：
  - `.tmp/e2e_fullstack/backend.log`
  - `.tmp/e2e_fullstack/frontend.log`

