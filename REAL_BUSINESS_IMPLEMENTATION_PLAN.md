# AgentForge v0.1 真实业务闭环实施方案 (FREEZE-LEVEL)

## 1. 系统当前真实阻塞点（精简版）

*   **OpenRouter 未完成真实连通验证**：模型网关尚未对接并验证 OpenRouter，导致执行引擎无真实模型支撑，处于空转或直接失败状态。
*   **Execution 链路断裂**：从 ExecutionEngine 到 ModelGateway，再到 OpenRouter 及最终的日志持久化（ExecutionLog）链路存在断层，无法追踪真实的执行轨迹。
*   **前端依赖 Hack 触发**：前端过度依赖 `createAgent` 的 hack 手段强制触发流程，缺乏独立的执行状态流转与真实数据绑定。

⸻

## 2. v0.1 唯一目标（冻结声明）

**本阶段唯一目标：**
打通真实 execution 闭环，使 `final_answer` 完全来自 OpenRouter 模型调用。

**非目标（绝对禁止在本阶段开发）：**
*   Chat UI
*   多轮对话（Session / Memory）
*   工具扩展（RAG、Web Search 等）
*   UI 重构

⸻

## 3. Phase C0：Execution 最小真实闭环（核心部分）

### 3.1 Execution Path
必须严格遵循以下单向执行链路：
`Agent` → `Execute API` → `ExecutionEngine` → `ModelGateway` → `OpenRouter` → `LLM` → `Response` → `ExecutionLog` → `API Response`

### 3.2 OpenRouter 调用约束
*   **SDK**：必须使用 OpenAI-compatible SDK。
*   **Base URL**：`https://openrouter.ai/api/v1`
*   **模型命名**：必须符合 OpenRouter 规范（如：`openai/gpt-4o-mini`）。

**最小连通性验证脚本：**
```python
from openai import OpenAI

client = OpenAI(
    api_key="OPENROUTER_API_KEY",
    base_url="https://openrouter.ai/api/v1"
)

resp = client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[{"role": "user", "content": "hello"}]
)

print(resp)
```
> **强声明**：如果该脚本执行失败，禁止进入后续 Execution 联调阶段。

### 3.3 必须完成的最小能力
1.  OpenRouter API 可独立调用成功。
2.  `execute` 接口能成功返回 `execution_id`。
3.  `execution` 过程及结果能完整写入数据库。
4.  `execution.status` 必须能正确扭转为 `success` 或 `failed`。
5.  `execution.final_answer` 必须真实来自 OpenRouter 的输出。

### 3.4 数据验收标准
`GET /executions/{execution_id}` 的返回必须符合以下 JSON 结构：
```json
{
  "code": 0,
  "message": "OK",
  "data": {
    "execution_id": "uuid-string",
    "agent_id": "uuid-string",
    "status": "success",
    "final_state": "FINISHED",
    "termination_reason": "SUCCESS",
    "steps_used": 1,
    "final_answer": "来自 OpenRouter 的真实回复文本",
    "react_steps": [
      {
        "step_index": 1,
        "thought": "模型的思考过程",
        "action": {
          "type": "finish",
          "final_answer": "来自 OpenRouter 的真实回复文本"
        },
        "observation": {
          "result": "Finished."
        },
        "state_before": "INIT",
        "state_after": "FINISHED"
      }
    ],
    "total_token_usage": {
      "prompt_tokens": 10,
      "completion_tokens": 20,
      "total_tokens": 30
    }
  }
}
```

### 3.5 CLI 联调路径
必须能完全脱离前端，仅依靠 CLI 完成闭环验证：

**1. Create Agent**
```bash
curl -X POST http://localhost:8000/agents \
-H "Authorization: Bearer <YOUR_TOKEN>" \
-H "Content-Type: application/json" \
-d '{
  "system_prompt": "You are a helpful assistant.",
  "model_config": {
    "model": "openai/gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 1000
  },
  "tools": [],
  "constraints": {
    "max_steps": 5
  }
}'
```

**2. Execute Agent**
```bash
curl -X POST http://localhost:8000/agents/<AGENT_ID>/execute \
-H "Authorization: Bearer <YOUR_TOKEN>" \
-H "Content-Type: application/json" \
-d '{
  "input": "测试 OpenRouter 连通性"
}'
```

**3. Get Execution**
```bash
curl -X GET http://localhost:8000/executions/<EXECUTION_ID> \
-H "Authorization: Bearer <YOUR_TOKEN>"
```

### 3.6 风险与强约束
*   **OpenRouter API 风险**：存在 API 不稳定或触发第三方限流的风险，底层异常需被全局捕获并规范化抛出。
*   **LLM 输出解析风险**：大模型输出格式不可控，`ExecutionEngine` 的 parser 必须具备强鲁棒性，处理非标准 JSON。
*   **执行路径约束**：Execution 必须允许无 `react_steps`（即直接 Finish）的成功路径。

⸻

## 4. Phase C1：前端接入（严格延后）

> **强声明**：只有在 Phase C0 通过 CLI 联调 100% 验收后，才允许执行本阶段。

**核心任务（仅限）：**
*   对接 `GET /executions/{execution_id}` 实现 polling execution 状态。
*   在界面上展示 `final_answer`。
*   在界面上展示 `react_steps`。
*(禁止进行任何超出此范围的 UI 设计细节重构)*

⸻

## 5. 删除或降级内容（必须执行）

以下内容在本阶段已被彻底删除或降级为 Future，禁止投入任何开发资源：
*   **多轮会话（Session）**：废弃，当前仅支持单次 Input/Output。
*   **Chat UI 重构**：废弃，沿用现有 Preview 组件展示结果。
*   **知识库 / 工具扩展**：废弃，不引入 RAG 或复杂外部工具。
*   **多模型 Routing**：废弃，强绑定 OpenRouter 单一入口。