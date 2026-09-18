# AgentForge 单智能体云端 Vibe Coding 平台实施规划 v1.0

版本：v1.0  
日期：2026-04-24  
状态：Freeze-Level Builder Plan  
适用模式：Builder / Coder 分离执行  
适用范围：AgentForge 从“单次执行型 Agent + 工具调用骨架”升级为“单智能体模式的一站式云端 Vibe Coding 开发平台”  

---

# 一、文档目标

本文档不是概念分析，也不是产品愿景文案。  
本文档的用途是：

1. 作为 Builder 阶段直接执行的总规划文档
2. 作为后续每个 Phase 设计输出与 Coder 实现的冻结边界
3. 保证前端、后端、插件市场、执行引擎改造时不脱离当前工作区真实实现
4. 保证所有新能力都能与当前已存在接口、服务、数据结构完成适配

本文档强约束：

1. 不允许模糊表述“增强能力”“优化体验”“完善平台”而不说明具体工程落点
2. 每个 Phase 必须指定开始前必读文档与代码文件
3. 每个 Phase 必须明确新增或修改的数据模型、服务、API、前端模块、测试
4. 每个 Phase 必须给出验收标准与禁止事项

---

# 二、当前工作区真实现状（必须先承认的事实）

## 2.1 当前已完成的真实基础

当前仓库已经具备以下真实能力：

1. FastAPI 后端主骨架已完成，包含统一异常出口、Auth、Quota、日志初始化、路由装配。
2. `Agent` CRUD 已完成，Agent 当前本质是单条 JSON 配置记录。
3. `ExecutionEngine` 已实现单智能体 ReAct + Tool Call 的最小闭环。
4. `ModelGateway` 已实现 OpenAI-compatible 模型调用封装。
5. `plugin_marketplace` 已实现扩展清单、工具目录、工具绑定、Builtin/MCP/API Adapter 路径。
6. 前端已经开始从固定 IDE Tabs 重构为 Builder Browser 动态 Tab 结构。
7. 运行日志与 ReAct Step Replay 已可查询。
8. 团队鉴权、JWT、配额、限流已具备基础闭环。

## 2.2 当前系统的真实边界

以下边界来自当前代码，不允许误判：

1. 当前 `/agents/{id}/execute` 是同步等待执行完成后直接返回，不是异步 Run/Job 模式。  
   参考：`backend/api/routes/agents.py`
2. 当前顶层产品实体仍然是 `Agent`，不是 `Project / Workspace / App`。  
   参考：`backend/models/schemas.py`、`backend/models/orm.py`
3. 当前执行结果中 `artifacts` 仍为空列表，平台还没有真正的“产物模型”。  
   参考：`backend/services/langgraph_execution_strategy.py`
4. 当前前端 `preview / skills / knowledge / deploy` 已有 IA，但大多数页仍是占位页。  
   参考：`frontend/src/components/workspace/builder/pages/*`
5. 当前 `DeployTabPage` 仍是前端本地模拟，不是真实部署链路。  
   参考：`frontend/src/components/workspace/builder/pages/DeployTabPage.tsx`
6. 当前 `preview_url / deployment_status / deployed_url` 只在前端状态层存在，后端 replay 尚未稳定产出这些字段。  
   参考：`frontend/src/features/execution/execution.types.ts`、`backend/services/execution_log_service.py`
7. 当前非 builtin 工具是“按次 install / execute / uninstall”的冷启动模式，不适合平台级高频持续构建。  
   参考：`plugin_marketplace/__init__.py`
8. 当前 Python Sandbox 明确属于 weak isolation，不能直接承担真正的云端构建工作区执行环境。  
   参考：`backend/core/sandbox/executor.py`

## 2.3 当前平台最核心的问题

当前 AgentForge 的问题不是“不会调工具”，而是“没有平台级运行上下文”：

1. 没有 `Project`
2. 没有持久 `Workspace`
3. 没有 `Run Queue`
4. 没有 `Artifact`
5. 没有 `Deployment`
6. 没有 `Knowledge` 数据模型
7. 没有真正的 `Skill` 运行层
8. 前端 Builder IA 与后端能力不对齐

结论：

当前系统已经是“执行内核 + 插件雏形 + Builder UI 壳”，但还不是“云端 Vibe Coding 平台”。

---

# 三、目标产品冻结定义（单智能体 P0）

## 3.1 P0 顶层目标

将 AgentForge 强化为：

一个以 `Project` 为中心、以单个 `Builder Agent` 为默认执行主体、具备云端工作区、技能、知识、预览、部署、日志闭环的一站式云端 Vibe Coding 开发平台。

## 3.2 P0 必须达成的产品结果

P0 交付后，系统必须支持以下完整路径：

1. 用户创建一个 `Project`
2. 用户配置单个 `Builder Profile`
3. 用户为项目绑定能力：工具、技能、知识、Secrets、扩展
4. 用户输入一句需求，平台创建异步 `Run`
5. Builder Agent 在云端工作区中执行：
   - 读取现有项目
   - 规划任务
   - 选择技能与工具
   - 写入/修改文件
   - 安装依赖
   - 运行构建
   - 启动预览
   - 失败时自动读取日志并自修复
6. 前端 Builder Browser 展示：
   - Preview
   - Agent Config
   - Skills
   - Knowledge
   - Run Logs
   - Deploy
7. 构建成功后返回真实 `preview_url`
8. 部署成功后返回真实 `deployed_url`
9. 每次 Run 都能回放结构化步骤、文件产物与错误诊断

## 3.3 P0 明确不做

以下内容禁止进入本期范围：

1. 多智能体协作
2. Workflow 画布编排
3. 社区模板市场
4. 多人实时协同编辑
5. 多 Workspace 并发竞争调度
6. 自定义模型自动路由策略
7. Browser automation 复杂代理链
8. 正式商用计费系统

---

# 四、全局冻结规则

## 4.1 架构冻结规则

以下边界必须保留，不允许跨层污染：

1. `Execution Strategy / Builder Strategy` 负责状态机与执行编排，不负责鉴权。
2. `ModelGateway` 只负责模型调用，不直接执行工具。
3. `Tool Runtime / Marketplace Runtime` 只负责工具执行，不做计划决策。
4. `Workspace Runtime` 只负责文件、命令、预览，不直接调模型。
5. `Deployment Runtime` 只负责部署，不持有 Agent 上下文。

## 4.2 接口冻结规则

1. 现有统一响应包 `{code, message, data}` 必须保留。
2. 新增平台 API 不允许绕过现有 Auth / Team 边界。
3. 现有 `/agents`、`/executions`、`/api/v1/marketplace/*` 在迁移完成前必须保持可用。
4. 前端在 Phase 迁移完成前不允许伪造 `preview_url`、`deployment_status`、`artifacts`。

## 4.3 迁移冻结规则

1. 不允许一次性删除 `Agent` 中心实现后再重做。
2. 必须采用“平台新实体新增 + 旧 Agent 兼容保留 + 前端逐步切换”的迁移方式。
3. `ExecutionLog / ReactStepLog` 现有日志资产必须继续保留，不允许直接废弃。

---

# 五、目标架构（P0）

## 5.1 顶层实体

P0 顶层业务实体必须调整为：

1. `Project`
2. `BuilderProfile`
3. `WorkspaceInstance`
4. `ProjectRun`
5. `RunArtifact`
6. `ProjectSecret`
7. `KnowledgeBase`
8. `KnowledgeDocument`
9. `Deployment`
10. `ReleaseVersion`

## 5.2 能力层级

P0 平台能力分为三层：

### Layer A：Tool

原子能力，必须直接映射到可执行接口：

1. 文件读写
2. 命令执行
3. 依赖安装
4. 预览启动
5. HTTP 调用
6. 搜索
7. Git 只读信息
8. 部署触发

### Layer B：Skill

可复用的多步工程能力：

1. 初始化项目
2. 创建页面
3. 新增组件
4. 接 API
5. 修复构建错误
6. 修复运行时错误
7. 准备部署

### Layer C：Builder Agent

负责：

1. 理解需求
2. 规划任务
3. 选择 Skill / Tool
4. 驱动 Workspace 执行
5. 根据构建结果进行自修复
6. 汇总产物与最终结论

---

# 六、分阶段实施规划

---

## Phase 0：基线审计、命名冻结、迁移方案冻结

### 0.1 开始前必须阅读

文档：

1. `docs/shared/AgentForge_v1.0.md`
2. `docs/shared/PHASE_STATUS.md`
3. `docs/shared/TECHNICAL_DEBT.md`
4. `docs/backend/AGENTFORGE_BACKEND_ARCHITECTURE_SPEC.md`
5. `docs/backend/AGENTFORGE_API_CONTRACTS.md`
6. `docs/backend/AGENTFORGE_DATA_MODELS_AND_DB_SCHEMA_SPEC.md`
7. `docs/backend/AGENTFORGE_EXECUTION_LOGGING_AND_AUDIT_SPEC.md`
8. `docs/backend/AGENTFORGE_STORAGE_AND_ARTIFACT_SPEC.md`
9. `docs/frontend/COZE_LIKE_BUILDER_BROWSER_REFACTOR_PLAN.md`
10. `docs/frontend/FRONTEND_FULL_PHASE_PLAN.md`

代码：

1. `backend/main.py`
2. `backend/api/routes/agents.py`
3. `backend/api/routes/executions.py`
4. `backend/models/schemas.py`
5. `backend/models/orm.py`
6. `backend/services/execution_engine.py`
7. `backend/services/langgraph_execution_strategy.py`
8. `backend/services/execution_log_service.py`
9. `plugin_marketplace/__init__.py`
10. `frontend/src/components/workspace/main/WorkspaceView.tsx`
11. `frontend/src/features/ui-shell/builderTabs.registry.ts`
12. `frontend/src/components/workspace/builder/pages/*`

### 0.2 Builder 必须输出

1. 当前实现与目标平台的差异矩阵
2. 平台统一命名词典
3. 兼容迁移策略
4. P0 范围冻结说明
5. 后续各 Phase 的依赖关系图

### 0.3 命名冻结

必须冻结以下命名，不允许在后续 Phase 中反复改词：

1. 顶层实体：`Project`
2. 默认智能体配置：`BuilderProfile`
3. 构建执行记录：`ProjectRun`
4. 云端运行上下文：`WorkspaceInstance`
5. 扩展后的能力集合：`Capability`
6. 工程复合能力：`Skill`
7. 文件/日志/URL 等结果对象：`RunArtifact`
8. 发布记录：`Deployment`
9. 公开可回滚版本：`ReleaseVersion`

### 0.4 兼容迁移策略

P0 采用以下兼容路径：

1. 保留现有 `Agent`、`ExecutionLog`、`ReactStepLog`
2. 新增平台实体，不立即删除旧实体
3. `Project.default_agent_id` 在 Phase 1 中建立，平台运行先复用现有 Agent 执行能力
4. 前端先切 `Project` 列表和 `Run` 流程，旧 `/agents` 页面在迁移期间可继续存在

### 0.5 验收标准

1. 命名词典冻结
2. 迁移路径明确
3. Phase 1 到 Phase 9 依赖顺序无循环
4. 明确哪些旧 API 保留，哪些新 API 新增

### 0.6 禁止事项

1. 禁止在未做 Phase 0 审计前直接开始建表和改路由
2. 禁止直接把 `Agent` 改名为 `Project`
3. 禁止前端先行发明后端不存在的数据结构

---

## Phase 1：平台域模型与数据库结构落地

### 1.1 开始前必须阅读

文档：

1. `docs/backend/AGENTFORGE_DATA_MODELS_AND_DB_SCHEMA_SPEC.md`
2. `docs/backend/AGENTFORGE_STORAGE_AND_ARTIFACT_SPEC.md`
3. `docs/backend/AGENTFORGE_AGENT_CONFIG_CONTRACTS.md`
4. `docs/backend/AGENTFORGE_AUTH_AND_PERMISSION_SPEC.md`
5. `docs/shared/PHASE_STATUS.md`

代码：

1. `backend/models/orm.py`
2. `backend/models/schemas.py`
3. `backend/services/agent_service.py`
4. `backend/services/authorization_service.py`
5. `plugin_marketplace/db/models.py`

### 1.2 本阶段目标

将当前“只有 Agent 和 Execution” 的数据域升级为“Project 驱动的平台数据域”，但不打断现有执行闭环。

### 1.3 必须新增的数据表

以下表必须新增，字段名必须在 Builder 文档中明确，不允许只写“若干字段”：

#### A. `projects`

必需字段：

1. `id`：UUID
2. `team_id`：UUID
3. `name`：TEXT
4. `description`：TEXT
5. `status`：TEXT，值域 `ACTIVE | ARCHIVED | DISABLED`
6. `default_agent_id`：UUID，可空
7. `active_workspace_id`：UUID，可空
8. `created_by`：TEXT
9. `created_at`：TIMESTAMP
10. `updated_at`：TIMESTAMP

索引：

1. `team_id`
2. `status`
3. `updated_at`

#### B. `project_builder_profiles`

必需字段：

1. `id`
2. `project_id`
3. `system_prompt`
4. `builder_mode`，值域 `VIBE_CODING`
5. `llm_provider_url`
6. `llm_api_key_encrypted`
7. `llm_model_name`
8. `runtime_config`：JSONB
9. `capability_flags`：JSONB
10. `constraints`：JSONB
11. `created_at`
12. `updated_at`

#### C. `project_capability_bindings`

必需字段：

1. `id`
2. `project_id`
3. `capability_type`，值域 `tool | skill | knowledge | integration`
4. `capability_id`
5. `enabled`
6. `config`：JSONB
7. `created_at`
8. `updated_at`

#### D. `workspace_instances`

必需字段：

1. `id`
2. `project_id`
3. `workspace_root`
4. `runtime_type`，值域 `local_dev | isolated_container | microvm`
5. `status`，值域 `CREATING | READY | BOOTING | BROKEN | ARCHIVED`
6. `preview_url`
7. `preview_status`
8. `last_booted_at`
9. `created_at`
10. `updated_at`

#### E. `project_runs`

必需字段：

1. `id`
2. `project_id`
3. `workspace_id`
4. `builder_profile_id`
5. `trigger_user_id`
6. `input_text`
7. `status`
8. `phase`
9. `termination_reason`
10. `final_answer`
11. `error_code`
12. `error_source`
13. `error_message`
14. `preview_url`
15. `deployed_url`
16. `token_usage`：JSONB
17. `created_at`
18. `started_at`
19. `completed_at`
20. `updated_at`

#### F. `run_artifacts`

必需字段：

1. `id`
2. `run_id`
3. `artifact_type`，值域 `file_change | command_log | preview | deployment | diagnosis | summary`
4. `path`
5. `title`
6. `summary`
7. `metadata`：JSONB
8. `created_at`

#### G. `project_secrets`

必需字段：

1. `id`
2. `project_id`
3. `secret_key`
4. `secret_value_encrypted`
5. `is_masked`
6. `created_by`
7. `created_at`
8. `updated_at`

#### H. `knowledge_bases`

必需字段：

1. `id`
2. `project_id`
3. `name`
4. `description`
5. `status`
6. `created_at`
7. `updated_at`

#### I. `knowledge_documents`

必需字段：

1. `id`
2. `knowledge_base_id`
3. `filename`
4. `mime_type`
5. `storage_path`
6. `status`
7. `chunk_count`
8. `created_at`
9. `updated_at`

#### J. `deployments`

必需字段：

1. `id`
2. `project_id`
3. `run_id`
4. `workspace_id`
5. `status`
6. `provider`
7. `preview_url`
8. `production_url`
9. `deployment_log_path`
10. `created_at`
11. `updated_at`

### 1.4 现有表的保留与扩展

以下旧表不删除，只做兼容扩展：

1. `agents`
   - 继续保留
   - 不再作为平台唯一顶层入口
2. `execution_logs`
   - 继续保留
   - 后续通过 `project_runs.legacy_execution_id` 或运行映射关联
3. `react_steps`
   - 继续保留
   - 后续作为详细回放底层来源

### 1.5 必须新增或修改的后端模块

必须新增：

1. `backend/services/project_service.py`
2. `backend/services/builder_profile_service.py`
3. `backend/services/project_capability_service.py`
4. `backend/services/workspace_registry_service.py`
5. `backend/services/project_secret_service.py`
6. `backend/services/knowledge_service.py`
7. `backend/services/deployment_service.py`

必须修改：

1. `backend/models/orm.py`
2. `backend/models/schemas.py`
3. `backend/services/authorization_service.py`

### 1.6 Builder 必须输出

1. 新旧实体关系图
2. 迁移时序图
3. 字段级 schema 说明
4. 索引与唯一约束说明
5. Team 边界如何落到新实体

### 1.7 验收标准

1. 新表定义完整
2. 新表与 `team_id / project_id / run_id / workspace_id` 关系清晰
3. 不存在 “后续补字段” 这类模糊项
4. 旧 `Agent` 兼容策略明确

### 1.8 禁止事项

1. 禁止把 Workspace 文件内容直接存入主业务表
2. 禁止把 Preview URL、Deployment URL 只存在前端状态
3. 禁止让 Secrets 明文返回给前端

---

## Phase 2：Project API、Builder Profile API、Capability API 落地

### 2.1 开始前必须阅读

文档：

1. `docs/backend/AGENTFORGE_API_CONTRACTS.md`
2. `docs/backend/AGENTFORGE_AUTH_AND_PERMISSION_SPEC.md`
3. `docs/backend/plugin-marketplace-api.md`
4. `docs/shared/PHASE_STATUS.md`

代码：

1. `backend/api/routes/agents.py`
2. `backend/api/routes/executions.py`
3. `backend/api/dependencies.py`
4. `backend/services/authorization_service.py`
5. `plugin_marketplace/api/routes.py`

### 2.2 本阶段目标

建立 `Project` 作为平台新入口，保留旧 `/agents`，但前端 Builder Browser 从本阶段开始优先对接新平台 API。

### 2.3 必须新增的 API

所有接口继续使用统一响应包 `{code, message, data}`。

#### A. Project

1. `POST /projects`
2. `GET /projects`
3. `GET /projects/{project_id}`
4. `PATCH /projects/{project_id}`
5. `DELETE /projects/{project_id}`

#### B. Builder Profile

1. `GET /projects/{project_id}/builder-profile`
2. `PUT /projects/{project_id}/builder-profile`

#### C. Capability Binding

1. `GET /projects/{project_id}/capabilities`
2. `PUT /projects/{project_id}/capabilities`
3. `GET /capabilities/catalog`

#### D. Secrets

1. `GET /projects/{project_id}/secrets`
2. `POST /projects/{project_id}/secrets`
3. `PATCH /projects/{project_id}/secrets/{secret_id}`
4. `DELETE /projects/{project_id}/secrets/{secret_id}`
5. `POST /projects/{project_id}/secrets/test-connection`

#### E. Knowledge

1. `GET /projects/{project_id}/knowledge-bases`
2. `POST /projects/{project_id}/knowledge-bases`
3. `POST /knowledge-bases/{kb_id}/documents`
4. `GET /knowledge-bases/{kb_id}/documents`
5. `DELETE /knowledge-documents/{document_id}`

### 2.4 API 字段冻结要求

以下字段必须明确进入 API contract，不允许用“前端自行推断”代替：

1. `project_id`
2. `builder_profile_id`
3. `workspace_id`
4. `preview_url`
5. `deployed_url`
6. `status`
7. `phase`
8. `capability_type`
9. `enabled`
10. `masked_value`

### 2.5 必须新增或修改的后端模块

新增：

1. `backend/api/routes/projects.py`
2. `backend/api/routes/project_capabilities.py`
3. `backend/api/routes/project_secrets.py`
4. `backend/api/routes/knowledge.py`

修改：

1. `backend/main.py`
2. `backend/api/dependencies.py`
3. `backend/services/authorization_service.py`

### 2.6 Builder 必须输出

1. 请求/响应示意
2. 与旧 `/agents` 的映射关系
3. Team 过滤与资源归属规则
4. 错误码映射清单

### 2.7 验收标准

1. 前端不再必须依赖 `/agents` 才能启动工作区
2. `Project` 及相关平台 API 可完整描述一个 Builder 项目
3. 所有新接口都带 Team 级 ownership 校验

### 2.8 禁止事项

1. 禁止在前端继续把 Project 伪装成 Agent
2. 禁止新平台接口绕过 `authorization_service`
3. 禁止新增 raw JSON 直出接口

---

## Phase 3：异步 Run 系统与 Worker 执行架构

### 3.1 开始前必须阅读

文档：

1. `docs/backend/AGENTFORGE_AGENT_RUNTIME_STATE_MACHINE_SPEC.md`
2. `docs/backend/AGENTFORGE_EXECUTION_LOGGING_AND_AUDIT_SPEC.md`
3. `docs/backend/AGENTFORGE_MODEL_GATEWAY_SPEC.md`
4. `docs/backend/AGENTFORGE_QUOTA_RATE_LIMIT_AND_BUDGET_SPEC.md`

代码：

1. `backend/api/routes/agents.py`
2. `backend/services/execution_engine.py`
3. `backend/services/langgraph_execution_strategy.py`
4. `backend/services/execution_log_service.py`
5. `backend/services/competition_manager_service.py`

### 3.2 本阶段目标

将当前同步执行模型改造为异步 Run 模型。

### 3.3 运行架构冻结

P0 必须采用以下执行拓扑：

1. HTTP API 只创建 `ProjectRun`
2. `ProjectRun.status` 初始写入 `QUEUED`
3. Worker 从队列中取任务
4. Worker 解析 Project / Builder Profile / Workspace 上下文
5. Worker 调用 Builder Strategy
6. Worker 逐步更新 `project_runs`、`execution_logs`、`react_steps`、`run_artifacts`
7. 前端使用 polling 查询 `GET /runs/{run_id}`

### 3.4 P0 Run 状态机

状态值必须冻结为：

1. `QUEUED`
2. `PLANNING`
3. `CODING`
4. `INSTALLING`
5. `TESTING`
6. `BOOTING`
7. `READY`
8. `DEPLOYING`
9. `SUCCEEDED`
10. `FAILED`
11. `CANCELLED`

### 3.5 必须新增的 API

1. `POST /projects/{project_id}/runs`
2. `GET /projects/{project_id}/runs`
3. `GET /runs/{run_id}`
4. `POST /runs/{run_id}/cancel`

### 3.6 必须新增的服务模块

1. `backend/services/project_run_service.py`
2. `backend/services/run_queue_service.py`
3. `backend/services/run_worker_service.py`
4. `backend/services/run_query_service.py`
5. `backend/services/run_artifact_service.py`

### 3.7 队列实现方式冻结

P0 直接使用现有 Redis 作为队列中间件：

1. DB 是 Run 状态的唯一事实来源
2. Redis 只负责调度队列，不负责最终状态持久化
3. API 创建任务时必须先写 DB，再投递 Redis
4. Worker 取到任务时必须再次读取 DB，禁止只依赖 Redis Payload

### 3.8 与现有 ExecutionEngine 的关系

必须采用以下方式，不允许硬改现有执行内核：

1. `ExecutionEngine` 继续保留
2. 新增 `ProjectRunOrchestrator` 作为 Worker 层入口
3. `ProjectRunOrchestrator` 负责：
   - 解析 Project 上下文
   - 准备 Workspace
   - 组装 Builder Strategy 入参
   - 调用底层执行策略
4. 不允许直接把队列逻辑写进 `backend/api/routes/agents.py`

### 3.9 Builder 必须输出

1. Run 状态机图
2. API 到 Worker 的时序图
3. Redis 队列使用方式
4. 失败重试与取消语义

### 3.10 验收标准

1. 创建 Run 接口在短时间内返回 `run_id`
2. Worker 能独立消费 Run
3. 前端 polling 不再依赖同步执行返回最终结果
4. Run 状态机字段与前端状态能一一对齐

### 3.11 禁止事项

1. 禁止继续让 `POST /execute` 阻塞到构建完成
2. 禁止把长时间构建逻辑留在 API 线程
3. 禁止前端根据 `status` 自行脑补 `phase`

---

## Phase 4：持久云端 Workspace Runtime

### 4.1 开始前必须阅读

文档：

1. `docs/backend/AGENTFORGE_STORAGE_AND_ARTIFACT_SPEC.md`
2. `docs/backend/AGENTFORGE_EXECUTION_ENGINE_REACT_PYTHON_SPEC.md`
3. `docs/backend/AGENTFORGE_PYTHON_SANDBOX_SECURITY_SPEC.md`
4. `docs/shared/TECHNICAL_DEBT.md`

代码：

1. `backend/core/sandbox/executor.py`
2. `backend/services/sandbox_service.py`
3. `plugin_marketplace/manifests/filesystem.yaml`
4. `plugin_marketplace/adapters/mcp_adapter.py`

### 4.2 本阶段目标

为单智能体 Builder 提供“可持续存在”的云端工作区，而不是一次性工具调用上下文。

### 4.3 工作区实现方式冻结

P0 必须满足以下实现要求：

1. Workspace 根目录必须由服务端统一分配
2. 根目录路径必须由配置项 `WORKSPACE_ROOT` 管理
3. 每个 Workspace 的物理目录路径必须包含 `team_id/project_id/workspace_id`
4. 文件系统是 Workspace 内容的唯一事实来源
5. DB 只保存 Workspace 元数据、Preview 状态与 Artifact 索引

### 4.4 Runtime 分层

Workspace Runtime 必须拆分为：

1. `WorkspaceRegistryService`
   - 创建 / 查找 / 归档 Workspace
2. `WorkspaceFileService`
   - 列目录 / 读文件 / 写文件 / 搜索文本
3. `WorkspaceCommandService`
   - 执行命令 / 保存 stdout / stderr / exit_code
4. `WorkspacePreviewService`
   - 启动 preview 进程 / 返回 preview_url / 检查健康状态

### 4.5 P0 明确实现方式

P0 不允许把当前 `PythonSandbox` 直接当成完整构建环境。必须做如下区分：

1. `PythonSandbox`
   - 继续保留
   - 仅用于低风险 Python Tool 或表达式执行
2. `Workspace Command Runtime`
   - 单独实现
   - 用于 `npm install`、`npm run dev`、`pytest`、`pnpm build` 等真实工程命令
3. 生产环境隔离目标
   - `isolated_container` 或 `microvm`
4. 本地开发兼容模式
   - 允许 `local_dev` Runtime，但必须通过 `workspace_root` 做目录隔离

### 4.6 必须新增的内部 API 或服务接口

内部服务必须支持以下方法：

1. `prepare_workspace(project_id)`
2. `get_workspace_tree(workspace_id, path)`
3. `read_workspace_file(workspace_id, path)`
4. `write_workspace_file(workspace_id, path, content)`
5. `search_workspace_text(workspace_id, query)`
6. `run_workspace_command(workspace_id, command, cwd)`
7. `start_workspace_preview(workspace_id)`
8. `get_workspace_preview_status(workspace_id)`

### 4.7 前端后续需要的外部 API

P0 至少预留：

1. `GET /projects/{project_id}/workspace`
2. `GET /projects/{project_id}/workspace/tree`
3. `GET /projects/{project_id}/workspace/file`
4. `PUT /projects/{project_id}/workspace/file`
5. `POST /projects/{project_id}/workspace/commands`
6. `GET /projects/{project_id}/preview`

### 4.8 Builder 必须输出

1. Workspace 生命周期图
2. 物理目录结构规范
3. 命令执行输出持久化方案
4. Preview URL 生成与回收方案

### 4.9 验收标准

1. 每个 Project 都能绑定一个持久 Workspace
2. Builder Agent 修改的文件能真实留在 Workspace 中
3. Preview URL 来自 Workspace Preview Runtime，而非前端模拟

### 4.10 禁止事项

1. 禁止把整个项目文件树塞进数据库 JSON 字段
2. 禁止直接复用当前 weak sandbox 承担完整 Web App 构建
3. 禁止让前端以 `window.open` 模拟 preview 成功

---

## Phase 5：Tool 平台升级与 Skill 一等公民落地

### 5.1 开始前必须阅读

文档：

1. `docs/backend/AGENTFORGE_TOOL_RUNTIME_AND_TOOL_CONTRACTS_SPEC.md`
2. `docs/backend/plugin-marketplace-api.md`
3. `docs/backend/AGENTFORGE_EXECUTION_ENGINE_REACT_PYTHON_SPEC.md`

代码：

1. `plugin_marketplace/__init__.py`
2. `plugin_marketplace/core/binding.py`
3. `plugin_marketplace/core/registry.py`
4. `plugin_marketplace/core/manager.py`
5. `plugin_marketplace/manifests/filesystem.yaml`
6. `plugin_marketplace/manifests/github.yaml`
7. `plugin_marketplace/manifests/brave_search.yaml`
8. `backend/services/marketplace_tool_adapter.py`

### 5.2 本阶段目标

将当前“工具目录 + 绑定 + 执行”的 Marketplace 升级为平台级 Capability 基座，并引入 `Skill`。

### 5.3 Tool 平台必须完成的改造

#### A. 作用域从 User 扩展到 Project

当前 `pm_user_extensions` 只支持 user 维度安装。P0 平台必须补齐 project 维度：

1. 新增 `pm_project_extensions`
2. Project 维度工具配置优先级高于 User 维度
3. Builder Browser 绑定工具时默认写入 Project 作用域

#### B. Adapter 生命周期升级

当前非 builtin 工具执行模式为：

`install -> execute -> uninstall`

P0 必须升级为：

1. Project 级 Runtime 预热
2. 同一 Project Run 内复用相同 Extension Runtime
3. 长时间空闲后按 TTL 回收

#### C. Tool 分类冻结

P0 平台工具分类冻结为：

1. `workspace_fs`
2. `workspace_shell`
3. `workspace_runtime`
4. `http`
5. `search`
6. `git`
7. `deploy`
8. `integration`

### 5.4 P0 初始工具清单（必须工程化落地）

P0 首批必须交付以下工具，不允许只写“若干基础工具”：

1. `workspace_fs/read_file`
2. `workspace_fs/write_file`
3. `workspace_fs/list_directory`
4. `workspace_fs/search_text`
5. `workspace_shell/run_command`
6. `workspace_runtime/start_preview`
7. `workspace_runtime/get_preview_status`
8. `http/request`
9. `search/web_search`
10. `deploy/start_preview_deploy`

现有 manifest 可复用映射：

1. `filesystem` 扩展作为 `workspace_fs` 的起点
2. `brave_search` 扩展作为 `search/web_search` 的起点
3. `github` 扩展在 P0 只开放只读能力，不开放写 PR

### 5.5 Skill 平台的实现方式冻结

P0 不直接把 Skill 塞进 `plugin_marketplace`，避免一次性破坏现有 Tool 路径。  
P0 采用独立 `builder_skills` 模块，定义：

1. `SkillDefinition`
2. `SkillBinding`
3. `SkillRuntime`
4. `SkillInputSchema`
5. `SkillOutputContract`

### 5.6 P0 必须交付的 Skill

以下 Skill 必须逐个定义依赖工具、输入、输出，不允许笼统描述：

1. `init_project`
   - 依赖：`workspace_fs`、`workspace_shell`
   - 输出：初始化文件列表、安装日志、启动结果
2. `create_page`
   - 依赖：`workspace_fs`
   - 输出：新增文件路径、页面路由说明
3. `create_component`
   - 依赖：`workspace_fs`
   - 输出：组件文件路径、引用关系
4. `wire_api`
   - 依赖：`workspace_fs`、`http/request`
   - 输出：API 调用点、环境变量需求
5. `fix_build_failure`
   - 依赖：`workspace_shell`、`workspace_fs`
   - 输出：错误原因、修改文件、修复结果
6. `fix_runtime_error`
   - 依赖：`workspace_runtime`、`workspace_shell`、`workspace_fs`
   - 输出：故障日志、修复结论
7. `prepare_deploy`
   - 依赖：`workspace_shell`、`deploy/start_preview_deploy`
   - 输出：构建摘要、部署结果

### 5.7 必须新增的后端模块

1. `backend/skills/definitions.py`
2. `backend/skills/runtime.py`
3. `backend/skills/catalog.py`
4. `backend/services/project_skill_service.py`
5. `backend/api/routes/skills.py`

### 5.8 Builder 必须输出

1. Tool 目录映射表
2. Skill 清单定义表
3. Project 级能力绑定规则
4. Runtime 预热与回收策略

### 5.9 验收标准

1. 前端 `skills` 页能读取真实 Skill Catalog
2. Project 级工具绑定能真实影响 Builder Run
3. 非 builtin 工具不再按次冷启动

### 5.10 禁止事项

1. 禁止把 Skill 简化成纯提示词文本
2. 禁止继续只用 `python_executor` 充当“万能工具”
3. 禁止在 P0 放开 GitHub 写操作与 PR 自动创建

---

## Phase 6：单智能体 Builder Strategy 重构

### 6.1 开始前必须阅读

文档：

1. `docs/backend/SINGLE_AGENT_REACT_PLAN.md`
2. `docs/backend/AGENTFORGE_EXECUTION_ENGINE_REACT_PYTHON_SPEC.md`
3. `docs/backend/AGENTFORGE_AGENT_RUNTIME_STATE_MACHINE_SPEC.md`
4. `docs/backend/AGENTFORGE_EXECUTION_LOGGING_AND_AUDIT_SPEC.md`

代码：

1. `backend/services/langgraph_execution_strategy.py`
2. `backend/services/agent_runtime_assembler.py`
3. `backend/services/model_gateway.py`
4. `backend/services/marketplace_tool_adapter.py`

### 6.2 本阶段目标

把当前“短回合工具执行器”升级成“面向工程构建的单智能体 Builder Strategy”。

### 6.3 Strategy 实现方式冻结

P0 必须采用“新策略类新增”方式，不直接把现有 `LangGraphExecutionStrategy` 改成不可控大杂烩。

必须新增：

1. `ProjectBuildExecutionStrategy`

职责：

1. 装配 Project Context
2. 生成结构化计划
3. 选择 Skill / Tool
4. 驱动 Workspace 执行
5. 读取构建日志
6. 失败后最多进行有限次修复
7. 产出 `RunArtifact`

### 6.4 P0 Builder 执行流程冻结

单次 Run 必须遵循以下固定阶段：

1. `load_project_context`
2. `summarize_workspace`
3. `retrieve_knowledge`
4. `generate_plan`
5. `select_skill_or_tool`
6. `apply_file_changes`
7. `install_dependencies_if_needed`
8. `run_build_or_test`
9. `boot_preview`
10. `diagnose_failure_if_any`
11. `retry_fix_if_allowed`
12. `emit_artifacts`
13. `finalize_answer`

### 6.5 P0 计划输出 Contract

Builder 规划阶段必须输出结构化 JSON，而不是只返回自由文本。  
计划 Contract 至少包含：

1. `goal`
2. `assumptions`
3. `selected_skills`
4. `selected_tools`
5. `target_files`
6. `commands_to_run`
7. `expected_artifacts`
8. `done_criteria`

### 6.6 P0 失败恢复规则

必须冻结为：

1. 预览启动失败：允许最多 2 轮修复
2. 构建失败：允许最多 2 轮修复
3. 同一错误签名连续重复：立即终止
4. 不允许无限重试

### 6.7 P0 记忆与上下文策略

禁止直接把完整文件树和所有日志无限堆入消息历史。  
必须新增以下摘要层：

1. `project_summary`
2. `workspace_summary`
3. `last_successful_preview_summary`
4. `last_failure_diagnosis`
5. `knowledge_retrieval_summary`

### 6.8 必须新增的后端模块

1. `backend/services/project_build_strategy.py`
2. `backend/services/project_context_service.py`
3. `backend/services/workspace_summary_service.py`
4. `backend/services/knowledge_retrieval_service.py`
5. `backend/services/run_diagnosis_service.py`

### 6.9 Builder 必须输出

1. Builder 状态机图
2. Plan JSON Contract
3. Retry / Loop Protection 规则
4. 摘要层设计

### 6.10 验收标准

1. 单次 Builder Run 能真实产出计划、文件变更、命令执行、预览结果
2. 失败诊断和修复步骤有结构化日志
3. `run_artifacts` 不再为空

### 6.11 禁止事项

1. 禁止继续只依赖 `final_answer` 展示结果
2. 禁止把所有失败都压成一个文本错误
3. 禁止在 Builder Strategy 内直接进行 HTTP 路由处理

---

## Phase 7：Knowledge、Secrets、Integrations、Preview、Deployment 闭环

### 7.1 开始前必须阅读

文档：

1. `docs/backend/AGENTFORGE_STORAGE_AND_ARTIFACT_SPEC.md`
2. `docs/backend/AGENTFORGE_AUTH_AND_PERMISSION_SPEC.md`
3. `docs/backend/plugin-marketplace-api.md`
4. `docs/shared/TECHNICAL_DEBT.md`

代码：

1. `backend/core/security.py`
2. `backend/services/authorization_service.py`
3. `plugin_marketplace/api/routes.py`
4. `frontend/src/features/execution/execution.types.ts`
5. `frontend/src/components/workspace/builder/pages/PreviewTabPage.tsx`
6. `frontend/src/components/workspace/builder/pages/DeployTabPage.tsx`

### 7.2 本阶段目标

把前端已有 IA 中最关键的四块接成真实闭环：

1. Knowledge
2. Secrets / Env Vars
3. Preview
4. Deploy

### 7.3 Knowledge 实现方式冻结

P0 知识库必须使用“文档上传 -> 切块 -> 索引 -> Retrieval”链路。

至少包含：

1. 文档上传存储
2. 文本切块
3. 文档状态机：`UPLOADING | INDEXING | READY | FAILED`
4. Retrieval API
5. Project 级绑定

### 7.4 Secrets / Env Vars 实现方式冻结

P0 必须支持：

1. 项目级 Secret 新增
2. 项目级 Secret 更新
3. 项目级 Secret 删除
4. 前端仅显示 masked value
5. Skill / Tool 在执行时按 key 引用 Secret，不默认向模型暴露明文

### 7.5 Preview 实现方式冻结

Preview 必须满足：

1. 后端真实写入 `project_runs.preview_url`
2. 后端真实写入 `workspace_instances.preview_url`
3. 前端 `PreviewTabPage` 只消费后端真实字段
4. `preview_phase` 不允许只由前端自行推导

### 7.6 Deployment 实现方式冻结

P0 部署只做两级：

1. Preview Deploy
2. Production Deploy 占位接口保留但默认不开启

必须支持：

1. 真实部署任务创建
2. `deployments` 表写入
3. `project_runs.deployed_url` 回填
4. 前端 `DeployTabPage` 删除 `setTimeout` 模拟逻辑

### 7.7 必须新增的后端 API

1. `POST /projects/{project_id}/preview/refresh`
2. `GET /projects/{project_id}/preview`
3. `POST /projects/{project_id}/deployments`
4. `GET /projects/{project_id}/deployments`
5. `GET /deployments/{deployment_id}`

### 7.8 必须新增或修改的前端模块

修改：

1. `frontend/src/components/workspace/builder/pages/PreviewTabPage.tsx`
2. `frontend/src/components/workspace/builder/pages/DeployTabPage.tsx`
3. `frontend/src/features/execution/execution.types.ts`
4. `frontend/src/features/execution/execution.store.ts`

新增：

1. `frontend/src/features/knowledge/*`
2. `frontend/src/features/deployment/*`
3. `frontend/src/features/projectSecrets/*`

### 7.9 Builder 必须输出

1. Knowledge 上传与索引流程
2. Secret 生命周期与权限模型
3. Preview 生成链路
4. Deployment 状态机

### 7.10 验收标准

1. `knowledge` 页不再是占位页
2. `deploy` 页不再是前端模拟页
3. Preview URL 与 Deployment URL 均由后端真实返回

### 7.11 禁止事项

1. 禁止在前端保留部署成功假数据
2. 禁止把 Secret 明文回显
3. 禁止把 Knowledge Retrieval 仅做文件列表展示而无实际检索

---

## Phase 8：Builder Browser 前端全量对接

### 8.1 开始前必须阅读

文档：

1. `docs/frontend/COZE_LIKE_BUILDER_BROWSER_REFACTOR_PLAN.md`
2. `docs/frontend/FRONTEND_FULL_PHASE_PLAN.md`
3. `docs/frontend/FRONTEND_TECHNICAL_DEBT.md`
4. `docs/shared/AgentForge v0.1 前后端对接完整实施计划 (Frontend Integration Plan).md`

代码：

1. `frontend/src/components/workspace/main/WorkspaceView.tsx`
2. `frontend/src/components/workspace/builder/BuilderTabContent.tsx`
3. `frontend/src/features/ui-shell/builderTabs.registry.ts`
4. `frontend/src/components/workspace/layout/CopilotPanel.tsx`
5. `frontend/src/components/workspace/chat/ChatComposer.tsx`
6. `frontend/src/components/workspace/layout/WorkspaceRail.tsx`
7. `frontend/src/features/execution/useExecutionPolling.ts`
8. `frontend/src/features/agent/agent.store.ts`

### 8.2 本阶段目标

让 Builder Browser 的 P0 Tab 全部接真实数据：

1. `preview`
2. `agent_config`
3. `skills`
4. `knowledge`
5. `run_logs`
6. `deploy`

### 8.3 前端状态中心必须重构

当前前端仍以 `Agent` 与 `Execution` 为核心状态。P0 平台必须新增以下 Store：

1. `project.store`
2. `builderProfile.store`
3. `capability.store`
4. `knowledge.store`
5. `run.store`
6. `workspace.store`
7. `deployment.store`

### 8.4 关键页面改造要求

#### A. 左侧 `WorkspaceRail`

必须从“Recent Agents”升级为：

1. Current Project
2. Recent Projects
3. Archived Projects
4. Recent Runs
5. Platform Navigation

#### B. `ChatComposer`

必须改为：

1. 发送请求到 `POST /projects/{project_id}/runs`
2. 获取 `run_id`
3. 触发 polling `GET /runs/{run_id}`

#### C. `CopilotPanel`

必须展示真实：

1. 当前 Phase
2. 计划摘要
3. Skill 调用
4. Tool 调用
5. Preview 状态
6. Deployment 状态
7. Artifact 摘要

#### D. `BuilderCapabilityPage`

必须拆分掉 P0 占位页，不允许继续复用一个通用占位组件承载 `agent_config / skills / knowledge`。

### 8.5 运行日志页要求

`run_logs` 页必须显示：

1. Run 顶层状态
2. Builder Phase Timeline
3. ReAct / Skill / Tool 细节
4. 文件产物
5. 错误诊断
6. Preview URL
7. Deployment URL

### 8.6 前端 polling 策略冻结

P0 继续使用 polling，不引入 SSE / WebSocket。  
必须满足：

1. 只对活跃 `run_id` 轮询
2. `SUCCEEDED / FAILED / CANCELLED` 自动停止
3. 页面切换不丢失 Run 状态
4. 切换 Project 时自动中断旧 Run 轮询

### 8.7 Builder 必须输出

1. 前端 Store 拆分图
2. Builder Tabs 与后端 API 映射表
3. Polling 生命周期图
4. 占位页替换清单

### 8.8 验收标准

1. `BuilderCapabilityPage` 不再承担 P0 真页内容
2. `DeployTabPage` 与 `PreviewTabPage` 均接真实后端
3. 左侧导航已从 Agent 心智切换为 Project 心智
4. 发送一句需求能驱动完整 Run 闭环

### 8.9 禁止事项

1. 禁止继续用 `Agent` 命名驱动整个前端主流程
2. 禁止保留“发起部署（P0 前端占位）”逻辑
3. 禁止把真实页面退化成展示文案页

---

## Phase 9：安全、可观测性、测试闭环与上线门槛

### 9.1 开始前必须阅读

文档：

1. `docs/backend/AGENTFORGE_PYTHON_SANDBOX_SECURITY_SPEC.md`
2. `docs/backend/AGENTFORGE_OBSERVABILITY_AND_MONITORING_SPEC.md`
3. `docs/backend/AGENTFORGE_EXECUTION_LOGGING_AND_AUDIT_SPEC.md`
4. `docs/backend/AGENTFORGE_TESTING_AND_ACCEPTANCE_SPEC.md`
5. `docs/shared/TECHNICAL_DEBT.md`
6. `docs/frontend/FRONTEND_TECHNICAL_DEBT.md`

代码：

1. `backend/core/sandbox/executor.py`
2. `backend/api/dependencies.py`
3. `backend/services/competition_manager_service.py`
4. `tests/integration/test_execution_engine.py`
5. `tests/integration/test_execution_logs.py`
6. `tests/integration/test_runtime_startup_execution.py`
7. `tests/e2e/test_full_agent_lifecycle.py`

### 9.2 本阶段目标

建立单智能体云端 Builder 的上线门槛，而不是只停留在“本地能跑”。

### 9.3 安全要求

P0 必须完成：

1. Workspace Root 路径逃逸防护
2. Secret 掩码与审计
3. Project 级能力绑定权限校验
4. Preview URL 权限隔离
5. Deployment 触发权限控制

### 9.4 可观测性要求

必须贯穿以下 Trace 维度：

1. `request_id`
2. `project_id`
3. `run_id`
4. `workspace_id`
5. `deployment_id`
6. `tool_id`
7. `skill_id`

### 9.5 测试矩阵

P0 测试必须新增以下类别：

#### A. Unit

1. Project Service
2. Run Queue Service
3. Workspace File Service
4. Skill Runtime
5. Secret Service

#### B. Integration

1. Project -> Run -> Workspace -> Preview 全链路
2. Capability Binding 生效路径
3. Knowledge Retrieval 生效路径
4. Deploy API 生效路径
5. 取消 Run 生效路径

#### C. E2E

1. 创建 Project
2. 配置 Builder Profile
3. 绑定 Skill / Tool
4. 上传 Knowledge
5. 发起 Run
6. 获取 Preview
7. 触发 Deploy

### 9.6 上线门槛

只有满足以下条件才允许宣称进入“云端单智能体 Builder 可用态”：

1. Run 异步链路稳定
2. Preview URL 真实可访问
3. Deploy 链路真实可回写
4. Knowledge 与 Secret 能影响执行结果
5. 至少 1 个真实 Web 项目模板从零构建成功
6. 至少 1 个真实失败场景可自动修复

### 9.7 Builder 必须输出

1. 安全风险清单
2. 可观测性字段清单
3. 测试矩阵与样例场景
4. 上线门槛清单

### 9.8 验收标准

1. P0 不再是“壳产品”
2. 平台核心页都接真实后端
3. 工程闭环可重复执行
4. 日志、产物、预览、部署、权限都能追踪

### 9.9 禁止事项

1. 禁止在 weak sandbox 基础上直接宣称支持生产级云端构建
2. 禁止没有真实 Preview / Deploy 就对外宣称 Builder 完成
3. 禁止只做 happy path 演示，不补失败路径测试

---

# 七、P0 统一模块落地清单

## 7.1 后端新增模块总表

P0 最终至少新增以下模块：

1. `backend/services/project_service.py`
2. `backend/services/builder_profile_service.py`
3. `backend/services/project_capability_service.py`
4. `backend/services/project_secret_service.py`
5. `backend/services/knowledge_service.py`
6. `backend/services/workspace_registry_service.py`
7. `backend/services/workspace_file_service.py`
8. `backend/services/workspace_command_service.py`
9. `backend/services/workspace_preview_service.py`
10. `backend/services/project_run_service.py`
11. `backend/services/run_queue_service.py`
12. `backend/services/run_worker_service.py`
13. `backend/services/run_query_service.py`
14. `backend/services/run_artifact_service.py`
15. `backend/services/project_build_strategy.py`
16. `backend/services/project_context_service.py`
17. `backend/services/knowledge_retrieval_service.py`
18. `backend/services/run_diagnosis_service.py`
19. `backend/services/deployment_service.py`

## 7.2 前端新增模块总表

1. `frontend/src/features/project/*`
2. `frontend/src/features/run/*`
3. `frontend/src/features/workspace/*`
4. `frontend/src/features/skills/*`
5. `frontend/src/features/knowledge/*`
6. `frontend/src/features/deployment/*`
7. `frontend/src/features/projectSecrets/*`
8. `frontend/src/components/workspace/builder/pages/AgentConfigPage.tsx`
9. `frontend/src/components/workspace/builder/pages/SkillsPage.tsx`
10. `frontend/src/components/workspace/builder/pages/KnowledgePage.tsx`
11. `frontend/src/components/workspace/builder/pages/WorkspaceFilesPage.tsx`
12. `frontend/src/components/workspace/builder/pages/CloudTerminalPage.tsx`

## 7.3 必须修改的现有核心模块

后端：

1. `backend/main.py`
2. `backend/models/orm.py`
3. `backend/models/schemas.py`
4. `backend/services/authorization_service.py`
5. `backend/services/execution_log_service.py`
6. `backend/services/marketplace_tool_adapter.py`
7. `plugin_marketplace/__init__.py`
8. `plugin_marketplace/core/binding.py`

前端：

1. `frontend/src/components/workspace/main/WorkspaceView.tsx`
2. `frontend/src/components/workspace/builder/BuilderTabContent.tsx`
3. `frontend/src/components/workspace/layout/WorkspaceRail.tsx`
4. `frontend/src/components/workspace/layout/CopilotPanel.tsx`
5. `frontend/src/components/workspace/chat/ChatComposer.tsx`
6. `frontend/src/features/execution/execution.types.ts`
7. `frontend/src/features/execution/execution.store.ts`
8. `frontend/src/features/execution/useExecutionPolling.ts`
9. `frontend/src/features/ui-shell/builderTabs.registry.ts`

---

# 八、P0 完成定义（Definition of Done）

只有当以下条件全部满足，P0 才算完成：

1. 平台顶层入口已从 `Agent` 升级为 `Project`
2. Builder Browser 六大核心页全部接真实后端
3. 异步 Run + Worker 已上线
4. Workspace 已持久存在
5. 至少 10 个工具可用，至少 7 个 Skill 可用
6. Knowledge、Secrets、Preview、Deploy 全部形成真实闭环
7. Run 有结构化 Artifact
8. 前端不再保留 P0 占位逻辑
9. 安全、日志、权限、测试达到上线门槛

---

# 九、最终判断

当前工作区最适合的路线不是“继续堆工具数量”，而是：

1. 先把平台顶层从 `Agent` 切换为 `Project`
2. 再把执行模式从同步 `execute` 切换为异步 `run`
3. 再把一次性工具调用切换为持久 `workspace + capability + skill`
4. 最后把前端 Builder Browser 接成真实平台

如果不先做这四步，即使继续增加更多工具和技能，也只会得到“工具更多的执行器”，而不是“扣子编程式云端智能体构造平台”。

