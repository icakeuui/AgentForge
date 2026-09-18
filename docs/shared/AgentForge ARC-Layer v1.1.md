# AgentForge ARC-Layer Phase X（Agent LLM 配置 + OpenAI-Compatible + Tool Runtime）

**版本**：v1.2（Freeze-Ready）  
**状态**：Freeze-Level  
**角色**：SOLO BUILDER  
**范围**：单 Agent 执行链路（ReAct + Tool Calling）  
**定位**：Agent Runtime Contract Layer（ARC-Layer）  

---

## 一、Phase 核心目标（最终收敛）

在不破坏现有 ReAct 执行引擎的前提下，实现：

### 1. Agent 级 LLM 配置（完全去中心化）
- Base URL（OpenAI-compatible）
- API Key（加密存储）
- Model Name
- System Prompt（description）
- 元信息（name / avatar）

### 2. Model Gateway 动态化（强约束）
- 从 env → Agent 配置驱动
- 严格无 fallback
- 每次请求动态构建 client（无状态）

### 3. 完整兼容 ReAct + Tool Calling
- ReAct Loop
- Function Calling
- Tool Runtime
- Observation 回流

### 4. 错误标准化（替代 ERROR_TERMINATED）
统一 `error.code`：
- `AUTH_FAILED`
- `MODEL_NOT_FOUND`
- `MODEL_CAPABILITY_MISMATCH`
- `INVALID_TOOL_CALL`
- `PROVIDER_RATE_LIMITED`
- `MODEL_OUTPUT_TRUNCATED`
- `NETWORK_ERROR`

---

## 二、Agent 能力边界（冻结声明）

### 1. ReAct 执行循环（不可变）
`system` → `user` → `assistant` → `tool` → `assistant` → …

### 2. Tool Calling（唯一机制）
- 必须依赖 LLM `tool_calls`
- 禁止 prompt hack JSON

### 3. Final Answer 判定（唯一规则）
`tool_calls == null && content != null` → **FINAL**

### 4. 错误处理机制
- **Tool error** → Observation（继续循环）
- **Model error** → Gateway Exception（终止）

### 5. 执行上限
- `max_steps` 强制终止

---

## 三、关键问题修复（冻结约束）

### 3.1 模型能力不匹配（强阻断）

**触发条件**：
- Agent 启用了 tools/skills
- 模型不支持 tool calling

**行为**：
- 抛出 `ModelCapabilityMismatchException`
- `execution.status = FAILED`
- `error.code = MODEL_CAPABILITY_MISMATCH`

**禁止**：
- fallback chat-only
- 忽略 tools
- 静默降级

### 3.2 Tool Calling 兼容子集（唯一允许）

**请求结构**：
```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "...",
        "parameters": {}
      }
    }
  ]
}
```

**响应结构**：
```json
{
  "tool_calls": [
    {
      "id": "...",
      "function": {
        "name": "...",
        "arguments": "{...JSON string...}"
      }
    }
  ]
}
```

**不支持**：
- 并行 tool calls
- 多工具同时执行
- streaming tool calls
- 非 function 类型

### 3.3 Gateway 行为边界（严格限制）

**允许**：
- 标准字段映射
- JSON 解析

**禁止**：
- NLP 推断 tool call
- 从自然语言猜工具
- 自动修复语义逻辑

### 3.4 finish_reason → execution 映射（冻结）

| finish_reason | execution.status | termination_reason |
| :--- | :--- | :--- |
| `stop` | SUCCEEDED | SUCCESS |
| `tool_calls` | RUNNING | - |
| `length` | TERMINATED | MODEL_OUTPUT_TRUNCATED |

**约束**：
- 必须保留 partial output
- 禁止丢弃内容
- 禁止误标 FAILED

### 3.5 Token Usage 策略

**优先级**：
1. provider usage
2. 本地估算（fallback）

**字段**：
- `usage_estimated: boolean`

**禁止**：
- 覆盖 provider usage
- 将估算当真实计费

---

## 四、数据与 API 契约（冻结）

### 4.1 Agent Schema
```typescript
{
  name: string;
  description: text;
  avatar_url: string?;
  llm_provider_url: string;
  llm_api_key: encrypted_string;
  llm_model_name: string;
  capability_flags: {
    supports_tools: boolean;
  };
}
```

### 4.2 API Key 安全规则
- 必须加密存储
- GET 永不返回明文
- 返回：`has_api_key: boolean`

### 4.3 SSRF 防护（强制）
**禁止**：
- `127.0.0.1`
- `192.168.*`
- 内网地址
- `localhost` / docker internal host

---

## 五、执行路径（唯一执行链）

`Agent` → `Load Config` → `Decrypt Key` → `Capability Check` → `Model Gateway` → `Tool Runtime` → `ReAct Loop`

---

## 六、Gateway 执行契约（新增关键补足）

**必须**：
- 每次请求新建 client（无状态）
- 使用 Agent 配置
- 使用 OpenAI-compatible 协议

**禁止**：
- 使用环境变量 fallback
- 使用默认 key
- 共享 client 状态

**新增：连接超时与重试策略（缺失补足）**
必须定义（否则不可冻结）：
- **timeout**: 30s（硬超时）
- **retry**: 0（禁止自动重试）

**禁止**：
- 隐式重试
- 多次请求 provider

---

## 七、异常体系（最终版）

### 7.1 统一格式
```json
{
  "error": {
    "code": "string",
    "message": "string"
  }
}
```

### 7.2 错误码全集（冻结）

| code | 含义 |
| :--- | :--- |
| `MISSING_API_KEY` | 未配置 |
| `INVALID_ENDPOINT` | URL错误 |
| `AUTH_FAILED` | key无效 |
| `MODEL_NOT_FOUND` | 模型不存在 |
| `MODEL_CAPABILITY_MISMATCH` | 不支持tool |
| `INVALID_TOOL_CALL` | JSON错误 |
| `PROVIDER_RATE_LIMITED` | 限流 |
| `MODEL_OUTPUT_TRUNCATED` | 输出截断 |
| `NETWORK_ERROR` | 网络错误 |

### 7.3 新增：错误出口约束（关键补足）

**必须满足**：
- 所有异常统一从 Gateway 抛出
- Execution Engine 不做错误包装
- UI 仅消费 `error.code`

**禁止**：
- 多层 error rewrite
- UI fallback message

---

## 八、UI/UX 设计（UI-UX Pro Max参与）

### 8.1 Agent Config Panel
- 名称 / Avatar / Description
- Base URL
- API Key（密码框）
- Model Name

**增强**：
- endpoint 实时校验
- key 不回显
- “连接测试”按钮

### 8.2 错误展示映射

| error.code | UI表现 |
| :--- | :--- |
| `AUTH_FAILED` | Key错误 |
| `MODEL_NOT_FOUND` | 模型不存在 |
| `MODEL_CAPABILITY_MISMATCH` | 不支持工具 |
| `PROVIDER_RATE_LIMITED` | 限流 |

### 8.3 ReAct Debug Panel

**展示**：
- Thought
- Action
- Observation

**错误**：
- 红色 `termination_reason`

### 8.4 Execution 状态 UI（严格绑定）
- `PENDING` → Initializing
- `RUNNING` → Thinking
- `SUCCEEDED` → final_answer
- `FAILED` → error
- `TERMINATED` → 中断

---

## 九、UI-UX Pro Max 总结（强制记录）

**参与范围**：
1. 配置交互设计（结构 + 校验 + 密钥安全）
2. 错误语义映射（`error.code` → 用户提示）
3. 执行可视化（ReAct + Tool）
4. 状态一致性（完全绑定 `execution.status`）
5. 安全体验（key 不回显 + endpoint 风险提示）

---

## 十、反模式（冻结阻断）

**禁止**：
1. Gateway fallback env key
2. UI 拼接错误信息
3. Tool calling 降级为 chat
4. 自动 retry provider
5. 解析自然语言 tool call
6. 多 execution 混用
7. 缓存 client 状态
