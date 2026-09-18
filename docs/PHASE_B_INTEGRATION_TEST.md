# AgentForge Phase B 前后端联调测试报告

**版本:** v1.1
**日期:** 2026-04-14
**状态:** ✅ 联调通过 (PASS)
**范围:** Phase B 前端真实输出验证阶段（Authentication, API Integration, CORS, Agent Creation）

---

## 1. 联调环境配置与启动流程

为了完整复现并测试 Phase B 的前后端联调，**必须开启 3 个独立的终端窗口**，分别用于启动后端服务、启动前端服务以及执行验证脚本/命令。

### 1.1 终端 1：初始化数据与启动后端服务
**职责:** 确保数据库表结构（特别是 UUID 类型的 Team 主键）正确初始化，并启动 FastAPI 后端。
**操作步骤:**
1. 进入项目根目录：
   ```bash
   cd /Users/laosun/Documents/personal_projects/AgentForge
   ```
2. 执行数据初始化脚本（创建正确的 UUID 团队数据）：
   ```bash
   export PYTHONPATH=$PYTHONPATH:. && python3 scripts/check_team.py
   ```
3. 启动后端服务（默认运行在 `http://localhost:8000`）：
   ```bash
   export PYTHONPATH=$PYTHONPATH:. && python3 backend/main.py
   ```
*(保持该终端运行，不要关闭)*

### 1.2 终端 2：生成 Token 与启动前端服务
**职责:** 获取最新的合法 JWT Token，更新前端环境变量，并启动 Vite 前端。
**操作步骤:**
1. 进入项目根目录，生成合法 Token：
   ```bash
   cd /Users/laosun/Documents/personal_projects/AgentForge
   export PYTHONPATH=$PYTHONPATH:. && python3 scripts/generate_token.py
   ```
2. 复制控制台输出的 Token 字符串。
3. 进入前端目录，编辑 `.env.local` 文件，将生成的 Token 填入：
   ```env
   VITE_API_URL=http://localhost:8000
   VITE_VALID_JWT_TOKEN=<你刚刚复制的Token>
   ```
4. 启动前端服务（强制运行在 `http://localhost:3000`）：
   ```bash
   cd frontend
   npm run dev
   ```
*(保持该终端运行，不要关闭)*

### 1.3 终端 3：执行联调验证测试
**职责:** 使用 `curl` 或自动化脚本直接调用后端接口，以及观察前端保存动作的后端日志。
**操作步骤:**
1. 进入项目根目录：
   ```bash
   cd /Users/laosun/Documents/personal_projects/AgentForge
   ```
2. 准备执行第 3 节中的具体测试用例命令。

---

## 2. 核心修复记录 (Troubleshooting Log)

在本次联调初期，系统遭遇了严重阻断性故障，现已全面修复：

1. **[CRITICAL] 鉴权与数据底层类型冲突修复 (500 Error)**
   - **问题:** 数据库中 `Team.id` 被初始化为 `int` (值为 1)，而 ORM (`models/orm.py`) 期望使用 PostgreSQL 特有的 `UUID`，导致鉴权时报错 `AttributeError: 'int' object has no attribute 'replace'`。
   - **修复:** 删除旧库，将 ORM 中的 UUID 字段统一替换为 SQLAlchemy 原生的 `sqlalchemy.types.Uuid` 类型，重置数据库并在 `check_team.py` 中强制生成标准的 UUID `00000000-0000-0000-0000-000000000001`，实现全链路 UUID 语义统一。
2. **[HIGH] 无效 Token 阻断修复 (401 Error)**
   - **问题:** 前端环境变量中的 Token 是使用旧密钥生成或早已过期，导致一直返回 `Invalid token`。
   - **修复:** 通过 `scripts/generate_token.py` 重新生成当前环境合法的 24 小时有效 Token，并注入到 `frontend/.env.local` 的 `VITE_VALID_JWT_TOKEN` 环境变量中。
3. **[MEDIUM] 跨域与开发地址混乱修复 (CORS Error)**
   - **问题:** 前端同时请求 `localhost` 和 `127.0.0.1`，导致 CORS 拦截。
   - **修复:** 统一前端启动端口为 `3000` (`package.json`)，并将后端 CORS 中间件的 `allow_origins` 明确锁定为 `["http://localhost:3000"]`。

---

## 3. 接口联调测试用例 (Test Cases)

请在**终端 3**中依次执行以下命令，验证各个场景是否符合预期。

### TC-01: 缺失 Token 的非法请求
- **操作:** 
  ```bash
  curl -i -X POST http://localhost:8000/agents -H "Content-Type: application/json" -d "{}"
  ```
- **预期结果:** 返回 401 状态码，响应包含 `"message": "Authorization required"`。
- **实际结果:** 401 Unauthorized, Code: 5000。
- **状态:** ✅ PASS

### TC-02: 无效/过期 Token 的非法请求
- **操作:** 
  ```bash
  curl -i -X POST http://localhost:8000/agents -H "Authorization: Bearer invalid" -H "Content-Type: application/json" -d "{}"
  ```
- **预期结果:** 返回 401 状态码，响应包含 `"message": "Invalid token"`。
- **实际结果:** 401 Unauthorized, Code: 5001。
- **状态:** ✅ PASS

### TC-03: 合法 Token 访问 (API 级别测试)
- **前置条件:** 
  > ⚠️ **非常重要**：你必须将下方命令中的 `<your-valid-token>` 替换为**终端 2** 中实际生成的 Token 字符串，不能直接复制执行带有尖括号的占位符！
- **操作:** 
  ```bash
  # 记得替换 <your-valid-token>！
  curl -i -X POST http://localhost:8000/agents -H "Authorization: Bearer <your-valid-token>" -H "Content-Type: application/json" -d '{"system_prompt": "You are a helpful assistant.", "model_config": {"model": "gpt-3.5-turbo", "temperature": 0.7, "max_tokens": 1000}, "tools": ["echo_tool"], "constraints": {"max_steps": 5}}'
  ```
- **预期结果:** 状态码 200 OK，返回创建成功的 UUID。
- **实际结果:** 200 OK，响应体包含有效 UUID（例：`{"code":0,"message":"Created successfully","data":{"id":"827112da-a6cb-42dd-a534-b3a23f34e261"}}`）。
- **状态:** ✅ PASS

### TC-04: 前端真实保存触发测试 (End-to-End 测试)
- **前置条件:** 终端 1 (后端) 和 终端 2 (前端) 正在运行。前端 `.env.local` 已配置正确的 Token。
- **操作:** 
  1. 打开浏览器访问 `http://localhost:3000`。
  2. 在界面中配置 Agent 参数并点击“保存”按钮。
  3. 观察终端 1 (后端) 的输出日志。
- **预期结果:** 
  - 前端界面提示保存成功。
  - 终端 1 (后端日志) 显示接收到 `POST /agents` 请求，处理成功并返回 HTTP 200。
  - 数据库中成功插入新的 Agent 记录。
- **状态:** ✅ PASS

---

## 4. 遗留与建议事项 (Next Steps)

1. **环境隔离自动化:** 当前前端的有效 Token 是通过脚本手动生成并写死在 `.env.local` 中的。建议在后续 Phase 中完善“登录/获取 Token”接口，或在前端启动脚本中自动拉取最新测试 Token。
2. **接口扩充验证:** 当前仅验证了 `POST /agents`。接下来应扩展至 `POST /agents/{id}/execute` 接口，以完成 Execution Engine (执行引擎) 链路的端到端联调。
3. **CORS 白名单扩展:** 线上部署阶段需将 CORS `allow_origins` 修改为真实生产域名。

---
**结论:** 
Phase B 前后端联调验证通过。核心接口 `POST /agents` 的鉴权与数据流转完全打通，前端可以无阻碍地进入后端的 Agent 业务逻辑。
