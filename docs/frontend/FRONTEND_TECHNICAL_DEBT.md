# Frontend Technical Debt - v0.1

## 一、文档说明
说明：
- 本文档记录 v0.1 前端阶段的所有技术债务
- 仅记录，不允许在当前阶段修复（除非阻断）
- 所有债务必须标注是否阻断交付

---

## 二、债务列表

- Date: 2026-04-13
- Phase: Phase A
- Title: 卡片层级与阴影表现不清晰
- Category: UI
- Priority: Low
- Status: OPEN
- Description: 当前虽然引入了 `industrial-card` 与 `glass-panel`，但在多层级嵌套（如 Preview 区 Execution Trace 的步骤卡片与父级背景）时，由于背景色均为近似的 `slate-800`，边缘对比度和阴影表现不够突出，导致视觉层级粘连。
- Risk: 复杂嵌套数据（如多步 react_steps）在较暗屏幕下可能难以分辨边界。
- Impact: 影响用户快速扫视日志流的体验，视觉上显得扁平。
- 是否阻断当前阶段：NO
- 建议处理阶段：v0.2
- 建议修复方向: 引入更多深色调阶（如 `slate-950`），并为内部嵌套卡片增加内阴影（`shadow-inner`）或更明确的亮色边框 (`border-slate-700/80`)。
- Deferred Justification: 当前阶段仅要求完成 v0.1 usability 验证前端骨架，核心目标是 UI Shell 的布局验证，不追求极致的视觉层级打磨。该视觉瑕疵不会阻断当前 demo 展示路径，因此允许延期至 v0.2 处理。

---

- Date: 2026-04-13
- Phase: Phase A
- Title: 组件间状态高度耦合风险
- Category: State
- Priority: Medium
- Status: OPEN
- Description: 目前所有核心状态（status, agentId, executionId, reactSteps 等）均直接定义在 `App.tsx` 的局部 state 中，通过 props 层层透传给 `Editor` 和 `Preview`。
- Risk: 随着 Phase B/C 引入真实 API 轮询和复杂的日志状态更新，`App.tsx` 将会急剧膨胀，触发全量 re-render。
- Impact: 导致不必要的重渲染，代码可维护性下降。
- 是否阻断当前阶段：NO
- 建议处理阶段：Phase B
- 建议修复方向: 引入轻量级状态管理（如 Zustand）或 React Context 将表单状态与执行结果状态分离。
- Deferred Justification: 当前阶段（Phase A）仅需建立状态位占位容器，以证明数据结构可支持后续开发。在尚未接入真实 API 前，引入状态管理库属于过度设计，因此延后至 Phase B 联调时重构。

---

- Date: 2026-04-13
- Phase: Phase A
- Title: 缺乏统一 Service / Request 层
- Category: Architecture
- Priority: High
- Status: OPEN
- Description: 目前仅完成了 UI 骨架，尚未建立与 backend 通信的统一 request 拦截器和 Service 封装层。API 调用逻辑很可能在 Phase B 被直接写在组件的 onClick 事件中。
- Risk: 接口域名、Auth Header (team_id)、全局 Error 处理策略将散落在各个组件内部。
- Impact: 如果后端 Contract 变更（如统一返回格式 `{code, message, data}` 的提取），前端需要大面积修改。
- 是否阻断当前阶段：NO
- 建议处理阶段：Phase B
- 建议修复方向: 创建 `src/services/api.ts` 封装 Axios/Fetch，统一处理 JWT Auth 和 response 拦截解包。
- Deferred Justification: Phase A 的目标严格限制为“无 API 真实调用的静态 UI 验证”，此时实现 Request 层无真实数据验证。此架构债务留至 Phase B 接入真实后端闭环时顺势完成。

---

- Date: 2026-04-13
- Phase: Phase A
- Title: 未设计 execution polling (长轮询) 策略
- Category: API
- Priority: High
- Status: OPEN
- Description: Backend Execution Engine 是异步执行的，但前端目前只有同步的 `running` 到 `success` 的 setTimeout 模拟。未定义如何安全地轮询 `GET /executions/{id}`。
- Risk: 若直接在组件内写 `setInterval` 且未处理组件卸载，会导致内存泄漏和幽灵请求。同时缺乏最大轮询次数或超时终止机制。
- Impact: 真实执行长耗时任务时，前端可能卡死或发送海量无效请求打爆后端。
- 是否阻断当前阶段：NO
- 建议处理阶段：Phase C
- 建议修复方向: 抽象专门的 `useExecutionPolling` Hook，内部封装基于状态机的轮询控制，明确 `FINISHED` / `TERMINATED` 停止条件和 503/429 降级策略。
- Deferred Justification: 长轮询依赖真实后端的 execution 状态流转机制，属于 Phase C 的明确目标范围。当前仅需通过 timeout 模拟 UI loading 表现即可完成 Phase A 的占位验收，故延期合理。

---

- Date: 2026-04-13
- Phase: Phase A
- Title: 输入组件风格未完全收敛
- Category: UI
- Priority: Low
- Status: OPEN
- Description: 基础的 Input 和 Textarea 使用了 `.industrial-input`，但 Range Slider（温度调节）、Toggle（工具开关）等非标准输入组件仍使用原生 HTML 元素配合 tailwind 类名硬编码拼接。
- Risk: 随着后续增加更多配置项（如多选标签），UI 一致性极易被打破。
- Impact: 代码存在冗余，新组件复用成本高。
- 是否阻断当前阶段：NO
- 建议处理阶段：v0.2
- 建议修复方向: 在 `src/components/common/` 下抽取独立的 `Switch`, `Slider`, `TagInput` 等原子组件。
- Deferred Justification: v0.1 前端核心任务是搭建后端能力演示壳，无需追求可复用组件库级别的代码整洁度。现有硬编码实现已满足可用性验证需求，不阻断 demo 演示。

---

- Date: 2026-04-13
- Phase: Phase A
- Title: 执行反馈与操作路径引导不足
- Category: UX
- Priority: Medium
- Status: OPEN
- Description: 用户点击“开始执行”后，仅有按钮本身变为 loading 状态和顶部极小的 status indicator。右侧 Preview 区域在未产生第一条日志前，缺乏明确的“正在等待引擎调度”的骨架屏或过渡动画。
- Risk: 用户在长耗时任务初期可能认为系统未响应，从而重复点击。
- Impact: 增加无效请求，降低产品的工业级可信度。
- 是否阻断当前阶段：NO
- 建议处理阶段：Phase C
- 建议修复方向: 在 Preview 区增加专属的 `ExecutionPending` 状态视图，明确提示“Engine Initiating...”并禁用再次执行。
- Deferred Justification: Phase A 的目标是建立静态占位，当前按钮的 loading 表现足以说明交互已触发。更细致的过渡动画属于锦上添花，可留至 Phase C 联调真实长耗时任务时一并补充。

---

- Date: 2026-04-13
- Phase: Phase A
- Title: Preview 区信息密度不合理
- Category: UI
- Priority: Low
- Status: OPEN
- Description: `react_steps` (Thought/Action/Observation) 的占位卡片字体与间距过大，在真实场景下，如果 Agent 进行了 5-10 轮 ReAct 循环，用户需要大幅滚动才能看到最终结果。
- Risk: 真实的长文本 Observation（如大段搜索结果）会瞬间撑爆容器，导致日志失去可读性。
- Impact: 日志追踪功能失去可用性，变成纯粹的数据堆砌。
- 是否阻断当前阶段：NO
- 建议处理阶段：Phase C
- 建议修复方向: 对 `Observation` 文本进行 `line-clamp` 折叠限制，并提供“展开/收起”交互；减小 `Thought` 的字体层级和 `padding`，提高单屏信息密度。
- Deferred Justification: 当前测试的 mockup 数据篇幅较短，信息密度问题尚未暴露。必须在 Phase C 获取真实 backend execution logs 后，基于真实数据分布来调整折叠逻辑才更准确，目前不阻断开发进程。

---

- Date: 2026-04-13
- Phase: Phase A
- Title: 全局统一 Loading / Error 策略缺失
- Category: API
- Priority: Medium
- Status: OPEN
- Description: 当前仅在 `Preview` 底部预留了 Error Card 占位，并未设计全局级别的 Toast 提示（用于处理网络错误、401 鉴权失败、创建 Agent 时的 400 校验错误等非执行级异常）。
- Risk: 接口报错可能被静默吞掉，导致用户无法感知。
- Impact: 用户在配置错误时（如漏填参数）无法得到有效修正引导。
- 是否阻断当前阶段：NO
- 建议处理阶段：Phase B
- 建议修复方向: 引入全局 Toast 组件（对齐 Style Guide 中的 Toast 规范），在 Request 拦截器统一拦截非 200 响应并弹出。
- Deferred Justification: 全局异常提示强依赖 API Request 层的建立，在 Phase A 纯静态环境下无法验证触发逻辑。该缺陷留至 Phase B 联调接口报错场景时修复。

---

- Date: 2026-04-13
- Phase: Phase A
- Title: 状态机不严谨
- Category: State
- Priority: Medium
- Status: OPEN
- Description: `idle | editing | saving | running | success | failed` 状态机的流转目前是基于字符串的松散判断。允许非法的状态跃迁（例如从 `running` 直接跳回 `editing` 而不终止执行）。
- Risk: 状态竞态条件下（如点击保存后立刻点击执行）可能导致 `agent_id` 未生成就开始轮询。
- Impact: 产生脏数据或引发前端不可预知的崩溃。
- 是否阻断当前阶段：NO
- 建议处理阶段：Phase B
- 建议修复方向: 明确定义状态跃迁图，例如 `editing -> saving -> idle -> running -> success/failed`。执行操作必须锁定左侧表单编辑。
- Deferred Justification: 当前前端尚未对接真实异步操作，竞态条件不会触发，仅用作 UI 视觉呈现控制。严谨的状态跃迁控制需结合 Phase B 的真实数据闭环实现，不阻断当前 Phase A 的结构验收。
- Date: 2026-04-14
- Phase: Phase B2
- Title: Dev Token Lifecycle Management
- Category: Dev Experience
- Priority: Low
- Status: OPEN
- Description: 当前开发态 Token 通过 dev 启动流程动态生成，并注入前端运行时环境变量，但未提供 Token 自动刷新机制和 Token 失效检测与恢复机制。
- Risk: 长时间运行的 dev session 可能遇到 token 过期。
- Impact: 需要手动重启前端 dev 进程。
- 是否阻断当前阶段：NO
- 建议处理阶段：Future (Post Phase C / Auth System Introduction)
- 建议修复方向: 引入真正的 Auth System 时一并解决生命周期管理。
- Deferred Justification: 该问题属于开发体验优化，不影响 Phase C 功能开发。

---

- Date: 2026-04-14
- Phase: Phase B2
- Title: No Persistent Auth State (Frontend)
- Category: Auth Architecture
- Priority: Medium
- Status: OPEN
- Description: 当前前端未实现任何形式的 Token 持久化（如 localStorage / cookie）。
- Risk: 页面刷新后依赖 dev 注入 Token，不支持用户级认证状态。
- Impact: 认证状态随刷新或重启丢失。
- 是否阻断当前阶段：NO
- 建议处理阶段：Auth System Phase
- 建议修复方向: 引入 localStorage 或 cookie 管理 token 持久化。
- Deferred Justification: Phase B2 明确禁止引入多 Token 来源，该限制是有意设计。

---

- Date: 2026-04-14
- Phase: Phase B2
- Title: Dev Token vs Production Auth Separation
- Category: Auth Architecture
- Priority: High
- Status: OPEN
- Description: 当前 Token 签发逻辑为开发态脚本驱动，尚未区分 Dev Token（脚本生成）和 Production Token（认证系统签发）。
- Risk: 存在误用风险（如果未隔离）。
- Impact: 当前 Token 机制不可直接用于生产环境。
- 是否阻断当前阶段：NO
- 建议处理阶段：Auth System Phase
- 建议修复方向: 建立正式的认证体系，区分 dev 和 prod token 签发逻辑，确保 Dev Token 仅存在于 scripts 层，不进入 backend API 正式认证路径。
- Deferred Justification: 当前仍处于开发验证期，生产隔离留待真实登录体系引入时处理。

---

- Date: 2026-04-14
- Phase: Phase B2
- Title: CORS Configuration Minimal Validation
- Category: Deployment Readiness
- Priority: Medium
- Status: OPEN
- Description: CORS 已完成环境变量驱动，但当前验证仅覆盖配置解析和基本允许 origin，未覆盖多域组合验证和生产域名策略验证。
- Risk: 生产部署配置可能存在遗漏或安全风险。
- Impact: 对生产部署有潜在风险，但对 Phase C 无影响。
- 是否阻断当前阶段：NO
- 建议处理阶段：Deployment / Production Hardening Phase
- 建议修复方向: 完善 CORS 的生产环境验证脚本和多源策略。
- Deferred Justification: 当前为本地联调阶段，CORS 变量化已满足本地需要。

---

- Date: 2026-04-14
- Phase: Phase B2
- Title: Verification Depth Limitation
- Category: Dev Experience
- Priority: Low
- Status: OPEN
- Description: `verify_phase_b2.py` 主要覆盖 Token 签发、配置解析、启动链路，未覆盖浏览器真实请求行为和 UI 层触发链路。
- Risk: 存在“脚本通过但 UI 异常”的理论风险。
- Impact: 需要额外的人工验证步骤。
- 是否阻断当前阶段：NO
- 建议处理阶段：Phase C E2E Test Introduction
- 建议修复方向: 引入端到端 (E2E) 测试框架覆盖真实 UI 请求行为。
- Deferred Justification: 已在 Phase Status 中要求 Manual UI Verification 缓解风险，深度自动化留待 E2E 阶段。

---

## 三、Debt Classification

| Type | Count |
|------|------|
| Dev Experience | 2 |
| Auth Architecture | 2 |
| Deployment Readiness | 1 |
| UI | 3 |
| State | 2 |
| UX | 1 |
| API | 2 |
| Architecture | 1 |

---

## 四、Overall Assessment

当前技术债均为：
- 非阻断型
- 非架构性错误
- 可在后续阶段自然演进解决

不阻止进入 Phase C。

---

## 五、Final Judgment

Phase B2 技术债可接受（ACCEPTABLE）

系统已具备进入 Phase C 的工程基础。

## Phase C2 Residual Debt

### 1. Frozen Model Dependency

#### Description
当前工具调用能力的稳定验收依赖冻结模型 `openai/gpt-4o-mini`。在未冻结模型或切换到其他模型时，tool_call 输出服从性与 ReAct JSON 格式稳定性存在波动。

#### Impact
- 不同模型可能绕过工具调用
- 不同模型可能输出不规范 JSON
- 验证结果的可复现性会下降

#### Decision
v0.1 工具调用阶段必须冻结模型，不允许在未重新验收的情况下随意切换。

#### Resolution Phase
Future (Model Policy / Provider Governance Phase)

---

### 2. Parser Implicit Fallback Risk

#### Description
当前 parser 在模型输出不规范时仍存在隐式降级为 finish 的风险。虽然本阶段通过 prompt 注入显著提升了 tool_call 命中率，但 parser 的失败模式仍可能掩盖部分格式错误。

#### Impact
- 模型输出不规范时，工具链可能被静默绕过
- 某些场景下表面 success，实际未触发工具调用

#### Decision
本阶段不重构 parser，仅通过强 prompt 约束实现最小 enablement。

#### Resolution Phase
Future (Parser Hardening Phase)

---

### 3. Runtime Error After-Explanation Behavior

#### Description
在 Python runtime error 场景中，模型在收到 tool error 后仍可能继续生成一轮解释性 finish，而不是立即终止。

#### Impact
- Step Error 已存在，但 execution 末尾可能附带额外解释
- 错误后的行为策略不够严格

#### Decision
当前行为不阻断 C2，因为 Step Error 已真实落库且可观测。

#### Resolution Phase
Future (Execution Policy Refinement Phase)

---

### 4. Tool Output Schema Fragility

#### Description
Python 工具输出结构对 observation schema 仍有较强依赖。若工具返回值结构与 schema 约束不完全一致，可能导致额外的 output validation 风险。

#### Impact
- 工具 success 结果可能被误判为 INVALID_OUTPUT
- 新增工具时需要谨慎对齐输出结构

#### Decision
本阶段通过修正当前工具路径实现通过，但未对全工具体系做统一治理。

#### Resolution Phase
Future (Tool Contract Normalization Phase)

---

### 5. Frontend Final Evidence Still Recommended

#### Description
虽然后端与日志层已经证明 Step Error 可真实产生，但仍建议补齐前端界面层面的最终截图证据，用于完整归档。

#### Impact
- 不影响 C2 通过
- 影响审计材料完整性

#### Decision
记为归档类债务，不阻断阶段关闭。

#### Resolution Phase
Immediate Follow-up / Documentation Phase

---

## Overall Assessment
当前 Phase C2 技术债均为非阻断型债务：
- 不影响真实工具调用能力
- 不影响 Step Error 产生
- 不影响前端消费 execution logs

系统已具备继续推进的工程基础。

## Final Judgment
Phase C2 技术债可接受（ACCEPTABLE）

 ## Phase C2 Residual Debt - Model Timeout Stability

### 1. Description

在真实联调过程中，ExecutionEngine 在调用 Model Gateway 时存在超时失败现象：

- 错误表现：
  - `Model call timed out after 15.0s`
  - Step 状态进入 FAILED
  - observation.error 写入：
    `Model Gateway Error: Model call timed out after 15.0s.`
  - 前端 Preview 正常渲染 Step Error 红框（含错误码与错误信息）

- 发生阶段：
  - LLM 调用阶段（ExecutionEngine → ModelGateway）
  - 未进入 parser / tool runtime / sandbox

---

### 2. Root Cause

当前 Model Gateway 使用固定超时策略：

- `default_timeout = 15.0s`
- 无 retry
- 无 fallback
- 无 streaming 中断恢复机制

在以下情况下容易触发：

- 模型响应延迟较高（如部分 OpenRouter / 第三方模型）
- prompt 体积较大（工具注入后 system_prompt 增长）
- 网络波动 / provider 抖动

---

### 3. Impact

#### 正面
- 错误已被完整捕获
- observation.error 正确写入 react_steps
- 前端可稳定渲染 Step Error 红框
- execution 状态流转正确（FAILED / TERMINATED）

#### 负面
- execution 在 Step 1 即终止
- 无法进入 tool_call 或后续推理阶段
- 用户体验受影响（表现为“内部错误”）

---

### 4. Current Decision

本阶段不修改 Model Gateway 策略：

- 不增加 retry
- 不增加 fallback
- 不调整 timeout
- 保持“严格失败（fail-fast）”语义

原因：

- 当前目标为验证工具调用链路（Phase C2）
- 超时问题不影响工具链路的正确性验证
- 已具备完整错误可观测性（满足阶段验收）

---

### 5. Resolution Strategy (Future)

将在后续阶段（Execution Policy / Stability Phase）处理：

#### 可能方案

1. **Timeout 调整策略**
   - 动态 timeout（按模型 / token / prompt 长度）
   - 或提升默认 timeout（如 30s）

2. **Retry 机制**
   - 单次重试（仅限 timeout）
   - 限制最大 retry 次数（防止雪崩）

3. **Provider Routing**
   - 慢模型 → 自动降级到 fast 模型
   - fallback provider

4. **Prompt 体积优化**
   - Tool instruction 压缩
   - system prompt 精简

5. **Streaming 支持（长期）**
   - 提前接收 token 防止超时
   - 中途终止策略

---

### 6. Phase Impact

- 不阻断 Phase C2：YES
- 不影响 Tool Invocation：YES
- 不影响 Step Error 渲染：YES
- 不影响前端闭环：YES

---

### 7. Final Judgment

该问题属于：

> 非阻断型运行时稳定性问题（Model Timeout）

当前状态：ACCEPTABLE  
处理阶段：Future Phase（Execution Stability / Policy）