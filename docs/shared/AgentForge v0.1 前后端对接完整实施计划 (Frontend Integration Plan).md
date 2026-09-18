# AgentForge v0.1 前后端对接完整实施计划 (Frontend Integration Plan)
## 整体目标
打通 AgentForge v0.1 真实业务闭环，将当前硬编码的前端界面完整接入已验证可行的后端单智能体（ReAct + Model Gateway）执行链路。

## 前置冻结约束（必须遵守） 
 
以下内容已在 Phase F0 / F1 完成并冻结： 
 
### 样式与基础设施（禁止修改） 
- frontend/src/main.tsx 
- frontend/src/styles/globals.css 
- frontend/src/styles/tokens.css 
- frontend/tailwind.config.js 
- frontend/postcss.config.js 
 
### 布局与结构（禁止重构） 
- 三栏结构（Sidebar / Workspace / Copilot） 
- AppShell / SidebarNav / TopHeader 
- PageContainer / PageHeader 
 
### UI 组件体系（禁止重写） 
- Button / Card / Input / Select / Badge / Alert 
- LogConsole / MessageBubbleRich / SkillCallBox 
 
### 强制规则 
1. F2-F4 期间禁止修改上述内容 
2. 若出现阻塞问题，仅允许最小修补 
3. 禁止在对接过程中重新设计 UI 
4. 禁止为适配后端而重构布局 

## Phase F1: 基础 API 客户端与状态管理层搭建
目标 ：建立统一的请求发送、响应拦截与全局状态管理，为后续接口对接提供稳定底座。

必须阅读的后端文档 ：

- docs/backend/AGENTFORGE_API_CONTRACTS.md (重点关注：统一返回结构 {code, message, data} 及错误码规范)
- docs/backend/AGENTFORGE_CONFIG_AND_ENV_SPEC.md (关注跨域配置与基础路由前缀)
实施计划 ：

1. API Client 封装 ：基于 Axios 或 Fetch 封装基础请求客户端，配置正确的 Base URL（例如 http://localhost:8000/api/v1 或 /api ）。
2. 拦截器实现 ：
   - 请求拦截器：注入必要的 Authorization 头部（若要求鉴权）。
   - 响应拦截器：统一解析 {code, message, data} 结构，将非 0 code 统一抛出为前端可捕获的业务异常。
3. 全局状态管理 ：设计并创建用于管理 Agent 和 Execution 状态的 Zustand Store（可扩展现有的 uiShell.store.ts ）。
4. 统一错误提示 ：结合现有的 Alert.tsx 或通知组件，实现 API 层错误的全局 UI 提示。
产物 ：

- 统一的 API Client 模块 ( src/lib/api.ts 或类似)
- 状态管理模块 ( src/features/agent/agent.store.ts )
- 全局错误拦截与提示机制
验收标准 ：

- 能够向后端 /health 接口发起请求，并正确解析返回包装格式。
- 模拟后端返回非 0 错误码时，前端能够自动弹出全局错误提示而不白屏。
## Phase F2: 智能体创建与工作区上下文闭环 (Agent Management)
目标 ：实现真实 Agent 的创建与上下文加载，替换前端写死的 "Code Reviewer Bot" 等静态占位符。

必须阅读的后端文档 ：

- REAL_BUSINESS_IMPLEMENTATION_PLAN.md (重点关注：3.5 CLI 联调路径中 POST /agents 的 Payload)
- docs/backend/AGENTFORGE_API_CONTRACTS.md (查看 GET /agents/{id} 的契约)
实施计划 ：

1. 服务定义 ：在 API 层增加 createAgent 和 getAgent 的请求方法。
2. UI 交互对接 ：
### Agent 创建规则（强制） 
 
1. Agent 创建仅允许通过用户主动操作触发： 
   - 点击 “New Agent Flow” 
   - 点击 “Create Agent” 
 
2. 页面加载行为必须为： 
   - 获取 Agent 列表 
   - 恢复最近使用的 agent_id 
 
3. 禁止行为： 
   - 禁止页面加载自动创建 Agent 
   - 禁止刷新页面重复创建 Agent 
   - 禁止隐式创建 Agent 
3. 工作区数据绑定 ：将 AgentsPage.tsx 和 WorkspaceView 中的硬编码标题、状态替换为后端加载的真实 Agent 数据。
产物 ：

- AgentService 中的 create 和 get 逻辑对接。
- 与真实 agent_id 绑定的工作区 UI（Header、Sidebar 状态更新）。
验收标准 ：

- 前端加载或主动创建时，Network 面板可见真实的 POST /agents 请求且成功返回。
- UI 顶部能够正确显示后端返回的 Agent ID 和配置状态。

## Execution Response Contract（强制） 
前端只允许依赖以下 execution 返回结构： 
{ 
  "execution_id": "string", 
  "status": "PENDING | RUNNING | SUCCEEDED | FAILED | TERMINATED", 
  "final_answer": "string", 
  "react_steps": [ 
    { 
      "step_index": number, 
      "action": { 
        "tool_id": "string", 
        "arguments": { ... } 
      }, 
      "observation": { 
        "ok": boolean, 
        "content": any, 
        "error": object | null 
      } 
    } 
  ], 
  "termination_reason": "string", 
  "total_token_usage": number, 
  "artifacts": [] 
} 
强制规则： 
1. 前端禁止访问未定义字段 
2. 禁止依赖后端隐式字段 
3. react_steps 必须顺序渲染 
4. final_answer 必须唯一来源于该字段 

## Execution Runtime Layer（强制） 
前端必须实现统一 Execution Runtime 层，禁止组件直接操作 execution 数据。 
### 1. Execution Store Contract 
{ 
  "current_execution_id": "string | null", 
  "status": "PENDING | RUNNING | SUCCEEDED | FAILED | TERMINATED", 
  "final_answer": "string | null", 
  "react_steps": [], 
  "termination_reason": "string | null", 
  "total_token_usage": number | null 
} 
### 2. Execution Actions 
仅允许： 
- startExecution(agent_id, input) 
- updateExecution(data) 
- finishExecution() 
- resetExecution() 
禁止： 
- 禁止组件直接 setState 
- 禁止多个 execution store 
### 3. Execution Flow（唯一入口） 
User Action 
↓ 
startExecution() 
↓ 
POST /execute 
↓ 
set execution_id 
↓ 
startPolling() 
↓ 
updateExecution() 
↓ 
finishExecution() 
### 4. Polling 更新规则 
每次 polling 必须： 
updateExecution({ 
  status, 
  react_steps, 
  final_answer, 
  termination_reason 
}) 
禁止： 
- 禁止局部更新 UI 
- 禁止拼接数据 
### 5. UI 分层 
1. Store 层 
2. Adapter 层 
3. UI 层（纯展示） 
禁止 UI 直接消费 API response 

## Phase F3: 真实执行链路与交互闭环 (Execution Loop)
目标 ：打通用户输入到后端 ReAct 引擎执行的过程，并能轮询获取执行结果。

必须阅读的后端文档 ：

- REAL_BUSINESS_IMPLEMENTATION_PLAN.md (重点关注：3.3 必须完成的最小能力，3.4 数据验收标准，3.5 CLI 联调路径中 execute 接口及 execution_id )
- docs/backend/SINGLE_AGENT_REACT_PLAN.md (关注修订后的 Execution Status Enum 状态定义)
实施计划 ：

1. 执行触发 ：将 ChatComposer.tsx （输入框）的发送动作绑定到 POST /agents/{id}/execute API。

## Execution Trigger Contract（强制） 
系统中仅允许以下触发方式： 
1. Chat 输入触发（主路径） 
2. Run Agent 按钮触发（辅助路径） 
触发规则： 
1. Chat 输入优先级最高 
2. Run Agent 必须： 
   - 使用当前输入框内容 
   - 输入为空 → 禁止触发 
3. 执行状态控制： 
- execution.status = RUNNING 时： 
  - 禁止再次触发 execute 
  - 禁用 Run Agent 按钮 
  - 禁用输入框发送 
4. 禁止行为： 
- 禁止多个 execution 并发 
- 禁止自动重复触发 execute 
- 禁止 UI 与 execution 状态不同步 
5. 请求防抖（强制） 
- execute 请求发出后，在收到 execution_id 前： 
  - 禁止再次触发 execute 
  - UI 必须进入 loading 状态 
- 若请求失败： 
  - 必须恢复输入状态 
  - 必须显示错误提示 
禁止行为： 
- 禁止重复点击触发多次 execute 
- 禁止 execution_id 未返回时启动 polling 

2. 状态流转与轮询机制 ：
   - 收到后端返回的 execution_id 后，立即将 UI 置为 RUNNING / PENDING 加载状态。
   - 实现轮询逻辑（Polling）：定时调用 GET /executions/{execution_id} 检查状态。
   - 当 status 变为 SUCCEEDED 、 FAILED 或 TERMINATED 时，停止轮询，并将完整 Execution 数据存入 Store。

### Execution Polling Contract（强制） 
 
1. 轮询间隔： 
   - 固定为 1000ms 
 
2. 终止条件： 
   - status ∈ {SUCCEEDED, FAILED, TERMINATED} 
 
3. 最大轮询时间： 
   - 120 秒 
 
4. 并发控制： 
   - 同一 execution_id 仅允许存在一个 polling 实例 
 
5. 生命周期管理： 
   - 切换 Agent 时必须停止旧 polling 
   - 切换页面时必须清理 polling 
   - 新 execution 开始时必须取消旧 execution polling 
 
6. 禁止行为： 
   - 禁止无限轮询 
   - 禁止多个 polling 同时运行 
   - 禁止 UI 不响应 polling 状态变化 

3. 防抖与并发控制 ：防止用户在执行未完成时重复发送请求。
产物 ：

- ChatComposer 真实发送逻辑对接。
- 针对 execution_id 的状态轮询 Hook ( useExecutionPolling )。
- 聊天区域的真实 Loading UI 反馈（防重复点击）。
验收标准 ：

- 用户发送消息后，正确触发 execute 接口并拿到 execution_id 。
- 前端开始定期请求 /executions/{execution_id} ，直至状态到达终态。
- 执行期间 UI 表现为明确的加载/思考中状态，且输入框被合理禁用。

## Execution Status UI Mapping（强制） 
状态与 UI 必须一一对应： 
1. PENDING 
- 显示：Initializing... 
- 禁用输入 
2. RUNNING 
- 显示：Thinking... 
- Chat 区显示 loading bubble 
- Debug 面板持续输出日志 
3. SUCCEEDED 
- 渲染 final_answer 
- 解锁输入 
4. FAILED 
- 显示错误卡片（红色） 
- 渲染 termination_reason 
- 解锁输入 
5. TERMINATED 
- 显示中断提示 
- 渲染 partial result（若存在） 
强制规则： 
1. UI 状态必须严格来自 execution.status 
2. 禁止使用本地 loading state 替代 
3. 禁止 UI 与后端状态不一致 

## Phase F4: 执行结果、步骤与日志渲染 (Results & Steps Rendering)
目标 ：将后端返回的 ReAct 执行轨迹、最终结果和 Token 消耗在各个面板中真实渲染。

必须阅读的后端文档 ：

- REAL_BUSINESS_IMPLEMENTATION_PLAN.md (重点关注：3.4 数据验收标准中 react_steps 、 final_answer 、 total_token_usage 的结构)
- docs/backend/SINGLE_AGENT_REACT_PLAN.md (关注修订后的 Artifacts Contract、Final Answer Contract 及 Observation Mapping)
实施计划 ：

1. 主输出区渲染 (AgentOutputPanel) ：
   - 提取 execution 数据中的 final_answer 。
   - 使用 Markdown 渲染组件（如 MessageBubbleRich.tsx ）将 final_answer 展示为智能体的最终回复。
2. 逻辑面板渲染 (LogicPreviewPanel) ：
   - 遍历 react_steps 数组。
### ReAct Steps 渲染规则（强制） 
 
1. 渲染数据来源： 
   - execution.react_steps 
 
2. 渲染结构： 
   - action（tool call）→ SkillCallBox 
   - observation → 关联展示在 action 下 
   - final_answer → 主输出区 
 
3. 关于 thought： 
   - 若后端返回 reasoning / thought 字段 → 可展示 
   - 若不存在 → 禁止前端生成或伪造 
 
4. 强制渲染对象： 
   - final_answer 
   - tool_call（action） 
   - observation 
   - termination_reason 
   - total_token_usage 
   - artifacts 
 
5. 禁止行为： 
   - 禁止伪造 thought 
   - 禁止拼接自然语言说明 
   - 禁止依赖非结构化数据 

3. 调试面板与状态带渲染 (DebugPreviewPanel / StatusStrip) ：
   - 提取 total_token_usage ，在面板中展示 Token 消耗统计。
   - 提取 termination_reason 或错误信息，若状态为 FAILED ，在面板中展示红色高亮错误。
4. 产物追踪 (Artifacts) ：若日志中包含文件变更产物，提供对应的标识展示。
产物 ：

- 真实数据驱动的 AgentOutputPanel 。
- 真实数据驱动的 LogicPreviewPanel （展示 ReAct Steps：Thought + Action + Observation）。
- 真实数据驱动的 Token 及错误日志展示（基于 termination_reason ）。
验收标准 ：

- 轮询结束后，主对话区能正确显示来自模型的真实回复文本（遵循 Final Answer Contract）。
- 左侧的 Logic Preview 面板能够正确拆解并按顺序展示智能体的 Thought 和 Tool Call 交互。
- 发生超时或错误时，前端能基于枚举化的 termination_reason 明确显示失败原因。

## Copilot vs Agent Execution（强制区分） 
1. Copilot Chat： 
- 仅调用 LLM 
- 不触发 ExecutionEngine 
- 不产生 execution_id 
2. Agent Execution： 
- 必须走 execute API 
- 必须产生 execution_id 
- 必须进入 polling 
禁止行为： 
- 禁止 Copilot 调用 tools 
- 禁止 Agent 跳过 execution_id 
