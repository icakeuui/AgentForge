# AgentForge Frontend v0.1 Full Phase Plan v1.1

## 一、全局冻结规则
本 Frontend Phase Plan 基于当前已经通过 Phase 9 验收的 backend contract。

前端开发期间强制执行：
1. 不允许修改 backend API
2. 不允许新增 backend 能力
3. 如发现 contract 不匹配，必须修改前端方案而非 backend
4. 所有前端能力必须严格服从当前 backend 真实实现
5. 本前端仅用于 v0.1 usability 验证，不是正式商用平台

系统级限制：
1. 单 Agent
2. 无画布
3. 无 workflow
4. 无多 Agent
5. 三栏结构：左（Agent 配置）、中（编辑与执行）、右（预览与日志）
6. 总工期必须小于 2 小时

## 二、总目标
在 2 小时内完成一个稳定可运行的前端 v0.1，用于验证并展示当前后端的真实能力：
- Agent 创建
- Agent 配置编辑
- Agent 单次执行
- 对话预览
- Execution 状态展示
- Execution Logs 查询结果展示
- Tool / Sandbox 执行反馈的基础可视化

## 三、前端能力边界冻结

### 3.1 必做范围
1. **左侧导航栏**
   - Logo / 项目标题
   - 控制台（占位）
   - 我的智能体（当前页）
   - 知识库（占位）
   - 设置（占位）
2. **中间编辑区**
   - 智能体名称
   - 简短描述
   - 系统提示词
   - 开场白
   - 温度
   - 最大 Tokens
   - 工具开关展示
   - 知识库标签展示
3. **右侧实时预览区**
   - 对话预览
   - 输入框
   - 执行按钮
   - loading / success / fail 状态
   - 基础执行反馈
   - 基础 execution / react_steps 结果展示
4. **后端真实接线**
   - 创建 Agent
   - 执行 Agent
   - 查询 execution 结果

### 3.2 明确不做
- 中间画布、工作流节点、拖拽编排
- 多智能体
- 知识库管理后台
- 用户系统、RBAC
- 社区广场
- 会话历史系统、长记忆
- 动态工具注册、动态技能市场
- 动画打磨、响应式适配精修

## 四、页面结构冻结
整体采用三栏布局：左（导航栏）、中（编辑器）、右（实时预览与日志）。

### 4.1 左侧导航栏
**用途**：提供产品感，不承载复杂真实业务。
**模块**：
- AgentForge 品牌区
- 控制台
- 我的智能体
- 知识库
- 设置
- 底部用户信息占位

**要求**：
- 导航可以是静态
- 当前高亮“我的智能体”
- 不要求完整路由系统

### 4.2 中间编辑器
**用途**：作为单智能体配置表单与执行入口。
**模块**：
- **Step 1：设定身份** - 头像占位、智能体名称、简要描述
- **Step 2：赋予灵魂** - 系统提示词、开场白
- **Step 3：回复设置** - 温度、最大 Tokens
- **Step 4：知识库与工具** - 知识库标签展示、网页搜索开关展示、代码执行开关展示
- **Step 5：执行入口** - 用户输入框、执行按钮、当前状态标签

**要求**：
- 全部采用表单式编辑
- 禁止任何画布感设计
- 禁止任何节点流设计

### 4.3 右侧实时预览区
**用途**：展示当前后端执行能力。
**模块**：
- 标题：效果实时预览
- 状态标签
- 消息区
- execution 信息区
- react_steps 区
- error 信息区

**要求**：
- 能看到 AI / 用户两种消息
- 能输入问题并触发执行
- 能展示执行中状态
- 能显示最终结果
- 能显示基础 execution 信息
- 能显示 react_steps
- 能显示 `error_code` / `error_source` / `error_message`

## 五、视觉风格冻结
严格遵循 dark-first 方向：
- 深色背景
- 工业感 + AI 工具感
- 少量玻璃拟态
- 高亮色使用 indigo / blue
- 卡片化布局
- 微交互只保留 hover / active 基础反馈

**视觉原则**：
- 优先深色版
- 优先清晰层级
- 优先结果区突出
- 不做复杂插画或重装饰

## 六、技术实现原则

### 6.1 前端技术目标
- 只做最小技术栈
- 只做一页主页面
- 优先实现稳定状态管理
- 优先与真实后端 API 接线

### 6.2 数据流原则
- 编辑区维护本地表单状态
- 点击保存时创建 Agent
- 创建成功后持有 `agent_id`
- 右侧输入后调用执行接口
- 执行接口返回 `execution_id`
- 再通过 `execution_id` 查询 execution 结果
- 结果回填到右侧预览区

### 6.3 状态原则
全局只允许以下状态：`idle`, `editing`, `saving`, `running`, `success`, `failed`

## 七、Phase 拆分（总工期 <= 2 小时）

### Phase A：页面骨架与静态布局
**开始前必须阅读**：
- `docs/backend/AGENTFORGE_V0_1_SCOPE_AND_BOUNDARY_FREEZE.md`
- `docs/backend/AGENTFORGE_API_CONTRACTS.md`
- `docs/backend/AGENTFORGE_AGENT_CONFIG_CONTRACTS.md`
- `docs/shared/PHASE_STATUS.md`
- `docs/frontend/AgentForge v0.1 前端总设计文档.md`
- `docs/frontend/AgentForge_UI_Style_Guide.md`

**Builder 任务输出**：三栏布局方案、左中右模块划分、UI 状态定义、Scope Freeze、开发顺序、验收标准。
**Coder 任务实现**：左侧导航、中间编辑区静态表单、右侧预览静态消息区、基础深色样式。
**Audit 检查**：页面是否三栏、是否无画布、是否无业务 API 调用、是否符合参考图方向。
**预期耗时**：20 分钟。
**验收标准**：页面可打开、三栏结构正确、深色风格成立、无画布、无节点流。

### Phase B：后端接口接线与主闭环
**开始前必须阅读**：
- Phase A 产物
- `docs/backend/AGENTFORGE_API_CONTRACTS.md`
- `docs/backend/AGENTFORGE_AGENT_CONFIG_CONTRACTS.md`
- `backend/api/routes/agents.py`
- `backend/models/schemas.py`
- `docs/shared/PHASE_STATUS.md`

**Builder 任务输出**：Agent 创建路径、Agent 执行路径、API Mapping、表单状态与执行状态、主闭环用户路径、验收标准。
**API Mapping**：
- 创建 Agent：`POST /agents`
- 执行 Agent：`POST /agents/{id}/execute`

**Coder 任务实现**：保存 Agent、持有 `agent_id`、执行 Agent、展示返回结果、展示 `request_id` / `execution_id` / `basic status`。
**Audit 检查**：是否真实调用 `POST /agents` 和 `POST /agents/{id}/execute`、是否无 mock、是否形成基本闭环。
**预期耗时**：45 分钟。
**验收标准**：能创建 Agent、能执行 Agent、能展示返回结果、页面不崩溃。

### Phase C：Execution 查询、React Steps 渲染与错误展示（Freeze-Level）

## 开始前必须阅读（严格顺序）

1. Phase B / B2 产物（前端鉴权链路 + 状态护栏）
2. docs/backend/AGENTFORGE_EXECUTION_LOGGING_AND_AUDIT_SPEC.md
3. backend/api/routes/executions.py
4. backend/services/execution_log_service.py
5. backend/models/schemas.py
6. docs/shared/PHASE_STATUS.md
7. docs/shared/TECHNICAL_DEBT.md

---

## Phase 目标

打通前端 Execution 查询链路，基于 `execution_id` 获取真实执行日志数据，并完成：

- execution 状态展示
- react_steps 执行过程可视化
- error 语义精准暴露
- loading / success / failed 生命周期展示

最终形成“前端执行调试闭环”。

---

## Scope Freeze（严格边界）

### 明确允许

- `GET /executions/{execution_id}` 查询
- polling（轮询）机制
- execution 元信息展示
- react_steps 列表渲染
- error 分层展示（global / step）
- loading / success / failed UI

### 明确禁止

1. 禁止 WebSocket / SSE
2. 禁止 execution 历史列表
3. 禁止日志检索 / 过滤
4. 禁止 DAG / 节点图形化
5. 禁止复杂 JSON viewer
6. 禁止使用 mock 数据替代真实接口
7. 禁止修改 backend schema / contract

---

## Builder 任务输出（必须完整）

1. execution 查询路径（Execution Path）
2. polling 生命周期设计
3. execution 数据结构映射（API Mapping）
4. react_steps 渲染结构设计
5. error 展示分层设计
6. execution 状态展示规则（loading / running / success / failed）
7. 前端状态与后端状态映射规则
8. 风险点与防护策略
9. 验收标准

---

## API Mapping（必须基于真实 backend）

### Endpoint

- `GET /executions/{execution_id}`

### 来源

- backend/api/routes/executions.py
- backend/services/execution_log_service.py

### 必须映射字段（禁止遗漏/伪造）

#### 顶层字段

- `status`
- `final_state`
- `termination_reason`
- `final_answer`
- `error_code`
- `error_message`
- `error_source`

#### 步骤字段

- `react_steps[]`
  - `step_index`
  - `step_status`
  - `thought`
  - `action`
  - `observation`
  - `error_code`
  - `error_message`
  - `error_source`

---

## Execution Path（用户操作路径）

1. 用户点击执行（Phase B 已实现）
2. 前端获取 `execution_id`
3. 进入 `running` 状态
4. 启动 polling（GET /executions/{execution_id}）
5. 持续更新 executionData
6. 判断终态：
   - success → 停止轮询
   - failed → 停止轮询
7. 渲染：
   - final_answer
   - react_steps
   - error 信息

---

## 核心冻结约束（必须执行）

### 1. Execution 状态分层（强制）

必须区分：

- 后端状态：`executionData.status`
- 前端展示状态：`executionViewStatus`

要求：

- 前端不得直接使用 raw status 控制 UI
- 必须封装映射函数：
  - `mapExecutionStatusToViewStatus`

禁止：

- 在组件中直接写 `status === 'success'`

---

### 2. 终态判断集中封装（强制）

必须实现：

- `isExecutionTerminalStatus(status)`

唯一用途：

- 控制 polling 停止

禁止：

- 在多个地方散写 `success/failed` 判断

---

### 3. Polling 生命周期（强制）

必须封装：

- `startPolling(executionId)`
- `pollExecutionOnce(executionId)`
- `stopPolling()`

要求：

- start 前必须 stop 旧 polling
- 组件卸载必须 stop
- 终态必须 stop
- pollingHandle 必须唯一

禁止：

- 多个 interval 并存
- 无 cleanup

---

### 4. Execution 状态清理（强制）

新执行前必须：

- 清空 executionData
- 清空 error
- 清空旧 steps
- 清空 pollingHandle

禁止：

- 上一轮 execution 数据污染下一轮

---

### 5. React Steps 条件渲染（强制）

必须满足：

- thought 存在才渲染
- action 存在才渲染
- observation 存在才渲染
- error 存在才渲染

必须支持：

- 字段缺失
- 空值
- 半结构数据

禁止：

- 假设步骤结构完整
- 因字段缺失导致崩溃

---

### 6. Error 分层展示（强制）

必须区分：

#### 全局 error

- 来源：execution 顶层
- 展示：全局横幅

#### 步骤 error

- 来源：react_steps[i]
- 展示：step card 内

禁止：

- 混为一个 error 区块
- 覆盖彼此

---

### 7. 单一 Polling Session（强制）

任意时刻：

- 只允许一个 polling

必须保证：

- 新 execution 清理旧 polling
- 页面卸载清理 polling

---

## UI 结构（右侧）

1. Execution Meta Header
   - status
   - termination_reason
   - steps_used

2. Global Error Area
   - error_code
   - error_message
   - error_source

3. Final Answer Area
   - final_answer

4. React Steps List
   - Step Card
     - step_index
     - step_status
     - thought
     - action
     - observation
     - step error

---

## 风险点（必须考虑）

1. 轮询风暴 → interval ≥ 2000ms
2. 长文本溢出 → scroll + wrap
3. 多 execution 竞态 → 强制清理 polling
4. 后端字段缺失 → 条件渲染
5. execution 状态扩展 → 不写死状态判断

---

## 验收标准（必须全部满足）

1. 必须真实调用 `GET /executions/{execution_id}`
2. execution 生命周期完整：
   - running → success / failed
3. polling 自动启动 / 自动停止
4. 可看到 react_steps 列表
5. 可看到 final_answer
6. 可看到 error（global + step）
7. 不依赖 mock 数据
8. 无重复 polling
9. 字段缺失不崩溃
10. UI 能形成调试闭环

---

## Audit 检查（必须通过）

1. 是否真实请求 execution API
2. 是否直接使用 backend schema
3. 是否存在 mock execution 数据
4. 是否存在多个 polling
5. 是否存在散落的 status 判断
6. 是否正确分层 error 展示
7. 是否正确处理字段缺失

---

## 预期耗时

30 分钟（仅限实现，不含调试扩展）

---

## Phase Gate Judgment

满足以下条件方可进入下一阶段：

- execution 查询链路打通
- polling 生命周期稳定
- react_steps 可视化
- error 展示准确
- 前端形成真实执行调试闭环

### Phase D：Demo 收口与交付可用性
**开始前必须阅读**：
- Phase C 产物
- `docs/backend/AGENTFORGE_V0_1_DELIVERY_CHECKLIST.md`
- `docs/backend/AGENTFORGE_TESTING_AND_ACCEPTANCE_SPEC.md`
- `docs/shared/PHASE_STATUS.md`

**Builder 任务输出**：最终演示路径、UI 收口范围、稳定性要求、禁止继续扩 scope、最终交付标准。
**Coder 任务实现**：防重复提交、输入与按钮状态控制、基础空状态、基础异常提示、演示默认文案与示例输入。
**Audit 检查**：是否可完整演示、是否无明显崩溃、是否仍然维持 v0.1 边界、是否满足 usability 验证目标。
**预期耗时**：20 分钟。
**验收标准**：输入 → 执行 → 查询 → 展示全链路成立、demo 可稳定展示、无扩 scope、可用于学院演示。

## 八、最终交付标准
必须全部满足：
1. 页面可启动
2. 三栏结构成立
3. 左侧导航成立
4. 中间编辑区可输入
5. 可创建 Agent
6. 可执行 Agent
7. 可通过 `execution_id` 查询结果
8. 右侧可展示最终结果
9. 右侧可展示 react_steps
10. 右侧可展示错误字段
11. UI 与参考图方向一致
12. 本地可用于学院演示

## 九、最终结论
本版本交付物本质是：
- 一个单智能体编辑器
- 一个后端能力演示壳
- 一个 usability 验证前端

不是：商用级产品、工作流平台、智能体广场。

**一句话总结**：
Frontend v0.1 的任务不是做一个完整 AI 平台，而是把 AgentForge v0.1 后端真实能力包装成一个可演示、可理解、可验证的单智能体产品壳。