# AgentForge 单智能体 ReAct + Tool Call 工程落地方案 v1.0（冻结版）

## 1. 总体目标 (Phase 目标)
构建稳定、可控、可验证的单智能体 ReAct 执行系统，基于 `plugin_marketplace` 作为工具底座。

必须实现：
1. 单智能体稳定运行（无随机崩溃）
2. 支持 function calling 驱动 tool call
3. 支持 ReAct（思考 → 调用 → 观察 → 继续）
4. 支持本地文件系统工具（读 / 写 / 列表）
5. 支持简单单文件代码生成并写入
6. 输出结果稳定可复现
7. 错误可解释，不允许 silent failure

## 2. 系统架构与 Data Flow
### 2.1 执行链路 (Execution Path & Data Flow)
```text
User Input 
   ↓ 
AgentService 
   ↓ 
ExecutionEngine 
   ↓ 
ReAct Loop 
   ↓ 
Model Gateway（LLM） 
   ↓ 
Tool Decision（function calling） 
   ↓ 
Plugin Marketplace（/tools/execute） 
   ↓ 
Tool Result（observation） 
   ↓ 
ReAct Loop 
   ↓ 
Final Answer 
```

### 2.2 严格边界
| 层级 | 职责 | 禁止行为 |
| --- | --- | --- |
| ExecutionEngine | 控制 ReAct 循环 | 禁止解析 JWT |
| ModelGateway | 调模型 | 禁止调用工具 |
| Marketplace | 执行工具 | 禁止做决策 |
| Tool Runtime | 执行工具逻辑 | 禁止访问 Agent 状态 |

## 3. 分阶段实现计划 (Implementation Plan)

### Phase 1：基础 ReAct 执行引擎（必须先完成）
**目标**：实现最小可运行 ReAct loop。

**必须实现**：
1. **ReAct Loop**（固定结构）：
```python
for step in range(MAX_STEPS): 
    response = call_model(messages, tools_schema) 
    if response.tool_call: 
        result = call_tool() 
        append_observation() 
    else: 
        return final_answer 
```

2. **固定参数**（不可动态）：
- `MAX_STEPS` = 6
- `MAX_TOOL_CALLS` = 4
- `TIMEOUT` = 30s

3. **停止条件**（必须全部实现）：
- 模型返回 final answer
- 达到 MAX_STEPS
- 连续 tool call 失败 >= 2
- 触发 Loop Protection（详见 Phase 6）

4. **错误处理**（必须实现）：
每个 tool call 必须执行 try/catch，标记 error，并按照 Observation Contract 返回。

### Phase 2：Tool Call 接入（基于 plugin_marketplace）
**目标**：完全接入 Marketplace 工具执行链。

**必须实现**：
1. **获取工具 schema**：
`GET /api/v1/marketplace/agents/{agent_id}/tools`
结果必须直接转换为：
```json
tools = [ 
  { 
    "type": "function", 
    "function": {...} 
  } 
] 
```

2. **执行工具 API 契约（强制统一）**：
`POST /api/v1/marketplace/tools/execute`
请求结构：
```json
{ 
  "tool_id": "string",
  "arguments": { ... },
  "context": { 
    "user_id": "string", 
    "team_id": "string",
    "request_id": "string",
    "agent_id": "string",
    "execution_id": "string"
  } 
} 
```
**强制约束**：
- 禁止使用 `tool_name`
- 禁止使用 `input`
- 必须使用 `tool_id` + `arguments`
- `arguments` 必须为合法 JSON，不允许字符串拼接

3. **Observation Contract 统一结构（必须新增）**：
```json
{ 
  "type": "tool_observation", 
  "tool_id": "string", 
  "ok": true, 
  "content_type": "text | json | error", 
  "content": "...", 
  "error": null 
} 
```
错误情况：
```json
{ 
  "type": "tool_observation", 
  "tool_id": "...", 
  "ok": false, 
  "content_type": "error", 
  "content": null, 
  "error": { 
    "code": "TOOL_EXECUTION_ERROR", 
    "message": "..." 
  } 
} 
```
**强制规则**：
- Observation 不允许纯文本拼接
- 必须结构化
- 必须区分 success / error

4. **禁止事项**：
- 禁止在 Agent 内直接调用文件系统
- 禁止绕过 Marketplace
- 禁止手写工具 schema

### Phase 3：基础工具集合（必须实现）
仅允许以下工具（第一阶段）：
1. `filesystem/read_file`: `{ "path": "string" }`
2. `filesystem/write_file`: `{ "path": "string", "content": "string" }`
3. `filesystem/list_dir`: `{ "path": "string" }`

**Filesystem Sandbox Policy 文件系统安全策略（强制）**：
1. 所有路径必须进行 normalize（绝对路径）
2. 禁止出现 `..`
3. 获取 realpath 后必须验证：`realpath.starts_with(SANDBOX_ROOT)`
4. 禁止符号链接逃逸
5. 所有 write 操作必须：
   - 验证父目录存在
   - 不允许覆盖系统路径

### Phase 4：Prompt 固化（关键）
**System Prompt（必须固定模板）**：
```text
You are an AI coding agent. 
Rules: 
1. Use tools when needed 
2. Never hallucinate file content 
3. Always read file before writing 
4. Keep output minimal and precise 
5. Stop when task is complete 

When using tools: 
- Always provide valid JSON 
- Never invent parameters 
- Use only provided tools 
```

### Phase 5：单文件代码生成能力（必须实现）
**工作流**：
User: 生成一个 React Button
↓
Agent:
1. list_dir
2. read_file（若存在）
3. generate code
4. write_file
5. return summary

**文件写入规则（强制）**：
1. 若目标文件存在：必须先调用 `read_file`
2. 若目标文件不存在：必须调用 `list_dir` 验证父目录
3. `write_file` 必须写入完整内容（full overwrite）
4. 禁止 partial patch

### Phase 6：稳定性控制（必须实现）
1. **Tool Call Budget**: max 4 次。
2. **Retry / Fallback 行为收紧（强制）**：
   - tool call 失败：retry 1 次（相同参数）
   - retry 仍失败：
     - 不再继续 tool call
     - 向模型追加 error observation
     - 模型必须生成 final answer（解释失败）
   - **禁止**：禁止无限 retry，禁止 fallback 到其他工具，禁止 silent retry
3. **Loop Protection 精确定义（强制）**：
   Loop Protection Trigger 条件（满足以下全部条件时触发终止）：
   1. 连续两次调用相同 `tool_id`
   2. `arguments` 完全相同（JSON deep equal）
   3. tool result 的 content hash 相同（SHA256）
   
   触发后行为：
   - 立即终止 ReAct Loop
   - 返回 structured failure answer
4. **Execution Step Log Contract（必须新增）**：
```json
{ 
  "execution_id": "string", 
  "step_index": 1, 
  "phase": "model_call | tool_call | observation | final_answer", 
  "tool_id": null, 
  "status": "success | error", 
  "payload": { ... }, 
  "timestamp": "ISO8601" 
} 
```
**强制规则**：
- 每一步必须记录
- 禁止跳过 logging
- payload 必须可序列化

### Phase 7：MCP / Git / GitHub（暂不实现，仅预留）
**当前禁止实现**：
- 多文件 patch
- Git commit / push
- PR 管理
- MCP 多工具编排
**仅允许**：
- read-only Git（后续 Phase）

## 4. 核心契约与执行状态 (Core Contracts)

### 4.1 Execution Status & Termination Reason Enum
**状态流 (Status Enum)**：
- `PENDING`
- `RUNNING`
- `SUCCEEDED`
- `FAILED`
- `TERMINATED`

```text
PENDING → RUNNING → SUCCEEDED 
                  → FAILED 
                  → TERMINATED 
```

**终止原因 (Termination Reason Enum) 强制定义**：
- `SUCCESS`: 模型成功输出 Final Answer 且无错误。
- `MAX_STEPS_REACHED`: 达到 `MAX_STEPS` 限制强制终止。
- `ERROR_TERMINATED`: 因系统级错误、工具重试彻底失败或 Loop Protection 触发导致的非正常终止。
- `TIMEOUT`: 执行整体超时导致终止。

### 4.2 Model Response Parsing Contract (单轮单 tool call 规则)
1. 仅解析 function call 字段
2. 必须提取：
   - `function.name` → `tool_id`
   - `function.arguments` → `arguments`
   - `tool_call_id` → 必须严格提取并在 Observation 返回时原样带回
3. `arguments` 必须 `JSON.parse` 成功
4. 若解析失败：
   - 视为模型错误
   - 不进入 tool call
5. **强制单轮单 tool call 规则**：
   - 若模型单次返回多个 `tool_calls`，**仅允许执行第一个**，强制抛弃其余。
   - 必须在 System Prompt 中明确限制模型单次仅调用一个工具。

### 4.3 Observation → LLM Message Mapping Contract（强制）
**规则**：
1. 每次 tool 执行后，必须将 Observation 转换为 LLM message
2. 不允许直接把 JSON 丢给模型
3. 必须使用 function response 格式，且**必须严格包含对应的 `tool_call_id`**。

**标准格式**：
role: "tool"
tool_call_id: "call_abc123"
name: tool_id
content: JSON.stringify({
  ok: boolean,
  content: string | object,
  error: object | null
})

**示例**：
```json
{ 
  "role": "tool", 
  "tool_call_id": "call_abc123",
  "name": "filesystem/read_file", 
  "content": "{\"ok\": true, \"content\": \"file content...\", \"error\": null}" 
} 
```

**强制规则**：
- content 必须是字符串（JSON stringify 后）
- 禁止直接传 object
- 禁止拼接自然语言描述
- 必须与 tool_id 一一对应
- 必须原样携带触发该工具调用的 `tool_call_id`，否则 API 调用将直接报错。

**错误情况**：
```json
{ 
  "role": "tool", 
  "tool_call_id": "call_abc123",
  "name": "filesystem/read_file", 
  "content": "{\"ok\": false, \"content\": null, \"error\": {\"code\": \"...\", \"message\": \"...\"}}" 
} 
```

**模型行为约束**：
- 模型必须读取 tool message
- 模型不得忽略 observation
- 模型下一步必须基于 observation 决策

### 4.4 Final Answer Contract
1. **提取规则**：当模型返回的响应中 `tool_calls` 为空，且 `content` 不为空时，该 `content` 必须被严格作为 `Final Answer` 提取。
2. **状态扭转**：成功提取 `Final Answer` 后，执行状态必须流转为 `SUCCEEDED`，终止原因为 `SUCCESS`。
3. **内容要求**：`Final Answer` 必须纯文本化，禁止包含内部调用的 JSON trace 数据。

### 4.5 Message Initialization Contract
1. **初始消息对**：启动 ReAct 循环前，消息数组 `messages` 必须严格通过以下两部分初始化：
   - `messages[0]`: `role: "system", content: <system_prompt>`
   - `messages[1]`: `role: "user", content: <user_input>`
2. **禁止行为**：禁止向初始上下文中夹带任何伪造的 assistant 历史回复或未声明的系统级隐藏 prompt。

### 4.6 Artifacts Contract
1. **文件类产物追踪**：凡工具执行导致沙盒内文件变更（如 `write_file` 成功），必须将产生的文件绝对路径及其 hash（如适用）记录在 execution_logs 的 `artifacts` 字段中。
2. **格式规范**：
```json
"artifacts": [
  { "type": "file", "path": "/sandbox/xxx/new_file.txt" }
]
```

### 4.7 超时控制 Contract (三级 Timeout)
1. **Execution Timeout (全局)**: 整体执行时间不得超过 60s。超时直接终止，状态为 `FAILED`，终止原因为 `TIMEOUT`。
2. **Model Timeout (单次推理)**: 单次大模型请求不得超过 15s。
3. **Tool Timeout (单次工具执行)**: 单次工具执行不得超过 10s。超出引发工具错误，按 Observation Error 处理。

## 5. Baseline (验收标准与测试用例)
**功能验证（必须能完成）**：
1. 读取文件并总结
2. 创建新文件
3. 修改单文件
4. 使用工具完成任务
5. 正确停止 ReAct

**稳定性验证**：
- 不死循环
- 不超过 step limit
- tool call 成功率 > 80%
- 错误可解释

**禁止通过的情况**：
- 模型无限循环
- tool 参数错误频繁
- 文件写入错误
- 崩溃或 silent failure

**5 个必须可复现的测试用例**：
1. **测试用例 1（读取总结）**：调用 `filesystem/read_file` 读取沙盒内已知文件，验证返回内容的准确性与格式。
2. **测试用例 2（新建文件）**：验证 Agent 能否成功调用 `filesystem/write_file` 在沙盒内创建目标文件并写入内容。
3. **测试用例 3（修改文件）**：验证 Agent 先 read 后 write，不出现 partial patch 且修改成功。
4. **测试用例 4（错误恢复）**：模拟工具调用失败一次，验证系统触发 1 次 retry；再次失败后触发 fallback 结束循环，未崩溃。
5. **测试用例 5（死循环阻断）**：提供连续产生相同输出的工具结果，验证 Loop Protection 能成功识别并阻断。

## 6. 执行顺序与最终交付物
**执行顺序（不可变）**：
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6（禁止跳阶段）。

**最终交付物（必须输出）**：
1. ReAct Engine 实现代码及结构
2. Marketplace Tool Adapter
3. 固定 Prompt 模板文件
4. Tool Schema 接入逻辑
5. 基础工具运行验证报告
6. 5 个测试用例脚本及测试结果（必须可复现）

## 7. 核心原则（必须遵守）
1. 工具统一从 Marketplace 走
2. Agent 不直接执行任何副作用操作
3. 所有行为可追踪
4. 所有结果可复现
5. 优先稳定性，不追求能力上限

