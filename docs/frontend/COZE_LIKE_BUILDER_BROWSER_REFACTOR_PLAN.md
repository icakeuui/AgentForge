# AgentForge 前端产品改造计划：Cloud Builder Browser（Coze-like MVP）

状态：计划文档（不包含实现代码）  
目标：将当前“本地 IDE / Cursor-like”心智，收敛为“Coze-like 云端智能体搭建平台 MVP”，同时保留并产品化中间主视图的类浏览器 Tab 交互。

---

## 1. 背景与问题定义

### 1.1 背景

当前产品方向需要从“本地 AI coder / Cursor-like 本地 AI IDE”收敛为“Coze-like 云端智能体搭建平台 MVP”。

### 1.2 核心问题

当前中间区域的“固定 IDE 标签栏”会让用户形成强烈的本地 IDE 预期（文件/终端/Git/调试流程等默认入口），这与云端 Builder 的默认体验冲突。

### 1.3 本次改造不变的价值

必须保留并产品化：中间主视图的类浏览器 tab 交互认知。

必须改变：不要把一整排固定 IDE 标签页默认展示出来；应改为浏览器式“动态 tabs”，由用户通过“+ 新标签页”按需创建。

---

## 2. 当前实现状态（基于工作区真实代码）

### 2.1 中间主视图组成

- `WorkspaceView`：顶部 `ContextHeader` + 固定 `WorkspaceTabBar` + `WorkspaceTabContent` 内容区。
- `WorkspaceTabBar`：硬编码固定 tabs 顺序与 icons。
- `WorkspaceTabContent`：用 if-chain 分发不同 tab 组件。

参考实现文件：

- `frontend/src/components/workspace/main/WorkspaceView.tsx`
- `frontend/src/components/workspace/main/ContextHeader.tsx`
- `frontend/src/components/workspace/tabs/WorkspaceTabBar.tsx`
- `frontend/src/components/workspace/tabs/WorkspaceTabContent.tsx`

### 2.2 固定主 tabs（IDE 心智来源）

现状固定主 tabs：

- `documents` / `terminal` / `browser` / `code-changes` / `agent` / `mcp` / `canvas` / `react-flow`

对应 store：

- `frontend/src/features/ui-shell/workspaceTabs.store.ts`
- `frontend/src/features/ui-shell/workspaceTabs.types.ts`

### 2.3 执行态对焦点的影响

现状：`WorkspaceView` 监听 `execution.store`，调用 `syncExecutionFocus`。

- 当执行状态为 `PENDING/RUNNING/FAILED` 时，会自动切到 `react-flow`。
- 这会把默认体验导向“调试流程”，与 Coze-like Builder 默认应停留的“预览/产物”体验相冲突。

相关文件：

- `frontend/src/features/execution/execution.store.ts`
- `frontend/src/features/execution/execution.types.ts`
- `frontend/src/features/ui-shell/workspaceTabs.store.ts`

### 2.4 Copilot 与中间 tabs 的耦合

现状：`CopilotPanel` 的 timeline 交互会触发 `openFile/selectBrowserLink/addCodeChange/focusReactStep/addCanvasPin`，并直接影响中间主 tabs。

相关文件：

- `frontend/src/components/workspace/layout/CopilotPanel.tsx`
- `frontend/src/components/workspace/copilot/timeline/mapExecutionToTimeline.ts`

---

## 3. 产品改造目标与原则

### 3.1 产品改造目标

将中间区域改造成“Cloud Builder Browser”：

- 像浏览器一样管理多个云端页面（tabs）。
- 默认体验必须是 Coze-like 云端智能体搭建，而不是 Cursor-like 本地 IDE。
- 中间主视图是云端沙箱构建产物与云端工具页容器，不是本地 IDE。

### 3.2 关键产品判断（强约束）

1. 保留类浏览器 tab 交互。
2. 固定标签按钮改为浏览器式动态 tabs（新增、关闭、切换、重命名）。
3. 默认只打开一个 `preview` 标签。
4. 点击 `+ 新标签页` 打开 `new_tab` 选择页。
5. 选择能力后才创建对应 tab。
6. 不再默认暴露“文档、终端、浏览器、代码变更、智能体、MCP、画布、ReAct 流程”等固定入口。
7. 即便保留 terminal/editor/git 等，也只能作为“开发工具”分类的可选卡片，且必须表达为“云端沙箱能力”，不能暗示本地文件系统。

---

## 4. 新的中间主视图结构（目标 IA）

### 4.1 顶部：浏览器式标签栏

- 默认 tab：`preview`
- 支持：多 tab、关闭、切换、重命名、状态提示
- 通过 `+` 打开 `new_tab`（能力选择页）
- 不把所有功能固定在顶栏

### 4.2 右上角：全局操作区

作为“当前活动 tab 或当前项目”的全局操作：

- 主题/外观
- 布局/面板可见性
- 复制/分享
- 新窗口打开
- 部署

### 4.3 主内容区：按 tab.type 渲染云端页面

- 默认：`preview`（Sandbox Preview）
- `new_tab`：能力选择页
- 其他类型：智能体配置、技能、知识库、运行日志、部署等

---

## 5. Tabs 类型规划

### 5.1 P0 必须规划（并作为默认可打开能力）

- `preview`：云端沙箱预览（iframe / preview state）
- `new_tab`：新标签页选择页
- `agent_config`：智能体配置
- `skills`：技能/工具选择
- `knowledge`：知识库
- `run_logs`：运行日志
- `deploy`：部署配置与发布结果

### 5.2 P1 可规划

- `workflow`：轻量工作流
- `connector`：集成服务/API 连接器
- `env_vars`：环境变量
- `database`：云端数据库
- `object_storage`：对象存储
- `analytics`：调用分析
- `versions`：版本与发布历史

---

## 6. 新标签页选择页（new_tab）信息架构

### 6.1 分组一：构建与预览

- 预览
- 智能体配置
- 技能
- 知识库

### 6.2 分组二：集成服务

- 集成管理（P1：connector）
- 环境变量（P1）
- 数据库（P1）
- 对象存储（P1）

### 6.3 分组三：发布与运营

- 部署
- 运行日志
- 版本历史（P1）
- 数据分析（P1）

### 6.4 分组四：开发工具（默认折叠/后置）

- 云端终端（不得称为本地终端）
- 云端编辑器（不得暗示本地文件系统）
- 版本控制
- 调试控制台

---

## 7. Tabs 交互规则（必须满足）

1. 点击顶部 `+`：
   - 若不存在 `new_tab`，创建并切换到 `new_tab`
   - 若已存在 `new_tab`，切换过去
2. 在 `new_tab` 点击某能力卡片的 `+`：
   - 创建对应 tab 并自动切换
   - 同类型 tab 默认只开一个（单例），除非允许多实例（例如 `run_logs`）
3. 每个 tab 字段：
   - `id` / `type` / `title` / `icon` / `closable` / `state` / `createdAt` / `resourceId?`
4. `preview` tab 不可关闭，或关闭后自动打开 `new_tab`
5. tab 状态：`idle/loading/ready/dirty/error`
6. 关闭 `dirty` tab 必须二次确认
7. 切换 tab 不应中断正在运行的构建任务
8. 构建任务状态由 Copilot + 全局 run store 维护，不绑死在 tab 生命周期

---

## 8. Copilot 区域改造（云端构建助手）

### 8.1 Copilot 必须展示的内容

- 用户需求
- 当前构建阶段
- 思考摘要
- 任务进度
- 工具调用卡片
- 技能调用卡片
- 沙箱状态
- 预览 URL
- 部署状态
- 错误与修复建议

### 8.2 禁止默认展示

- 禁止默认展示完整 raw ReAct JSON。
- 详情通过“查看详情”进入 `run_logs` tab。

### 8.3 ReAct 流程的定位

- 不作为默认 tab。
- 作为运行日志/详情的一部分（可展开或跳转查看）。

---

## 9. Preview Tab 状态机（产品态）

`preview` tab 需要支持：

- `empty`：等待用户描述要构建的智能体/应用
- `planning`：正在规划
- `building`：正在构建云端沙箱产物
- `booting`：沙箱启动中
- `ready`：显示 preview iframe
- `failed`：显示失败原因、重试、打开运行日志
- `deployed`：显示部署成功状态和访问链接

说明：该状态机不应与某个 tab 的生命周期强绑定；构建任务属于全局 run/build 状态。

---

## 10. 数据模型规划（前端 store 设计建议）

### 10.1 新增：builderTabs.store（建议新增，而非复用 workspaceTabs.store）

原因：现有 `workspaceTabs.store` 的数据结构与命名强绑定 IDE 子域（documents/browser/terminal/codeChanges/reactFlow），继续复用会把 IDE 心智带入 Builder。

建议 store 结构：

- `tabs: BuilderTab[]`
- `activeTabId: string`
- `openTab(request)`：走 tab factory
- `closeTab(id, { force? })`
- `renameTab(id, title)`
- `setActiveTab(id)`
- `setTabState(id, state)`：状态/dirty/error

### 10.2 Tab Factory

输入：`{ type, title?, icon?, resourceId?, params? }`  
输出：完整 `BuilderTab`（补齐 id/createdAt/closable/singleton 规则）。

### 10.3 Tab Registry

用于：

- 统一 tab 的默认标题/icon/是否单例/渲染组件
- 避免 if-chain 内容分发

### 10.4 Preview State

建议作为 `execution.store`（或未来 `run.store`）的派生 UI 状态：

- `preview_phase`
- `preview_url`
- `sandbox_status`
- `deployment_status`

### 10.5 Build Run State

建议与现有 `execution.store` 的衔接策略：

- P0：保留 `execution.store` 作为 run 的单一来源（当前已经存在轮询与快照更新），并扩展字段以覆盖 preview/deploy 状态。
- P1：当后端出现更清晰的 run API 后，可将 `execution.store` 演进为 `run.store`（或拆分），但需保持旧字段向后兼容，避免大规模重构。

### 10.6 Copilot Activity State

现状 timeline 直接由 `mapExecutionToTimeline` 从 execution 快照映射。

建议：

- P0：继续用映射，但“查看详情”目标改为 `run_logs` tab，而不是 `react-flow`。
- P1：当后端提供 `activity_events`，timeline 改为消费 events，execution 快照只作为状态汇总。

---

## 11. 与现有 stores 的衔接（避免跨生命周期绑死）

### 11.1 uiShell.store

继续承担：

- 左侧/右侧面板折叠与宽度
- 最大化面板状态（如仍保留）

新增/规划：

- 主题/外观切换入口（如 P0 需要）
- “面板可见性”作为 Builder 的全局操作区能力

### 11.2 execution.store

继续承担：

- 当前 run 的状态、步骤、错误、产物（P0）

扩展规划：

- preview_url、build_phase、deployment 状态、token usage 更丰富结构

### 11.3 agent.store

继续承担：

- 当前 agent 的选择与配置加载

演进建议：

- 逐步将“配置编辑”从 Drawer/事件迁移到 `agent_config` tab（减少“IDE 弹窗配置”的认知）。

---

## 12. 后端 / API 规划（本次不实现，但必须在路线中标注）

需要的 API（后续阶段）：

- 创建构建任务（run）
- 查询构建状态
- 获取 preview_url
- 获取 activity_events
- 获取 tool_calls / skill_calls
- 创建 deployment
- 查询 deployment 状态
- 获取 run logs
- 管理 knowledge / skills / integrations / env vars

---

## 13. P0 / P1 / P2 里程碑

### 13.1 P0（必须交付）

- 中间主视图替换为“浏览器式动态 tabs”
- 默认仅打开 `preview` tab
- `+` 打开 `new_tab` 选择页
- 从 `new_tab` 能打开：`agent_config/skills/knowledge/run_logs/deploy`
- Copilot 变为“云端构建助手”，默认不展示 raw ReAct JSON
- 执行态不再强制切到“ReAct 流程”页面（改为在 `run_logs` 查看详情）

### 13.2 P1（增强）

- connector/env_vars/database/object_storage 等集成类页面可用
- run_logs 支持更完整筛选与回放体验
- deploy 页面可展示发布历史与回滚

### 13.3 P2（平台化）

- workflow/analytics/versions 等运营与协作能力

---

## 14. 涉及文件与模块清单（P0 重点）

以下模块在 P0 很可能涉及改动或退场：

- `frontend/src/components/workspace/main/WorkspaceView.tsx`
- `frontend/src/components/workspace/main/ContextHeader.tsx`
- `frontend/src/components/workspace/layout/CopilotPanel.tsx`
- `frontend/src/components/workspace/layout/WorkspaceRail.tsx`
- `frontend/src/components/workspace/debug/ReActDebugPanel.tsx`
- `frontend/src/components/workspace/output/AgentOutputPanel.tsx`
- `frontend/src/features/ui-shell/uiShell.store.ts`
- `frontend/src/features/execution/execution.store.ts`
- `frontend/src/features/execution/execution.types.ts`
- `frontend/src/features/agent/agent.store.ts`
- `frontend/src/styles/tokens.css`
- `frontend/src/styles/globals.css`

以及现有“固定 IDE tabs”相关模块将被替换或降级：

- `frontend/src/features/ui-shell/workspaceTabs.store.ts`
- `frontend/src/features/ui-shell/workspaceTabs.types.ts`
- `frontend/src/components/workspace/tabs/WorkspaceTabBar.tsx`
- `frontend/src/components/workspace/tabs/WorkspaceTabContent.tsx`

---

## 15. 验收标准（P0）

### 15.1 默认体验

- 进入工作区后，中间顶部只显示一个 `preview` tab。
- 不再默认出现“文档/终端/浏览器/代码变更/智能体/MCP/画布/ReAct 流程”等固定入口。

### 15.2 新标签页选择

- 点击 `+`：
  - 若无 `new_tab`，创建并切换到 `new_tab`
  - 若已有 `new_tab`，直接切换
- 在 `new_tab` 点击能力卡：创建对应 tab 并切换。

### 15.3 Tab 行为

- `preview` 不可关闭，或关闭后自动打开 `new_tab`。
- 关闭 `dirty` tab 有确认。
- 切换 tab 不中断构建任务。

### 15.4 Copilot 行为

- 默认不展示完整 raw ReAct JSON。
- “查看详情”会打开 `run_logs` tab（而不是切到固定 `react-flow` 主 tab）。

### 15.5 去 IDE 心智

- terminal/editor 仅作为 `new_tab` 中“开发工具”折叠分组可选项。
- 任何终端/编辑器文案必须表述为“云端沙箱终端/云端沙箱文件编辑器”，不得暗示本地文件系统。

---

## 16. UI/UX 在本次任务中的职责范围（P0）

- 定义 Cloud Builder Browser 的信息架构与命名体系（避免 IDE 语义）。
- 输出 `new_tab` 选择页的分组、卡片规格（标题、描述、icon、状态、禁用态、提示文案）。
- 输出 Tabs 交互规范：新增/关闭/重命名/dirty 确认/状态角标。
- 输出 Copilot 信息呈现结构（阶段、进度、调用、预览、部署、错误建议），并定义“查看详情”跳转到 `run_logs` 的规范。

---

## 17. 关键约束总结（防止用户误以为是本地 IDE）

- 默认只给 `preview`，所有其他能力通过 `+` 按需打开。
- 顶部 tabs 是“云端页面实例”，不是“本地 IDE 模块按钮”。
- terminal/editor 必须带“云端沙箱”限定词，且默认隐藏在“开发工具”折叠分组。
- ReAct 流程不作为默认主 tab；详情进入 `run_logs`。

