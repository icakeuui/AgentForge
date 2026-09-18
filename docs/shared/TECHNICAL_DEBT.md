### TECHNICAL_DEBT.md 

- Date: 2026-04-08
- Phase: Phase 0 - 环境与项目骨架
- Debt:
  - 当前仅实现基础 /health 探针，后续可根据运维需要扩展 readiness / liveness 拆分
  - 当前错误码仅包含最小集合，后续需与 AGENTFORGE_ERROR_CODE_AND_FAILURE_HANDLING_SPEC.md 全面对齐
  - 当前仅完成日志基础设施，后续需补充结构化审计字段与 execution 级 tracing
- Impact:
  - 不影响 Phase 0 验收通过
  - 对后续 Phase 2、Phase 5、Phase 6 有依赖
- Planned Fix Phase:
  - Error code alignment: Phase 8
  - Execution trace enhancement: Phase 6
  - Health endpoint refinement: Deferred / 运维阶段
- Status: RESOLVED
- Fix Phase: Phase 8
- Summary: 已完成 1000~5000 整型错误码体系与全链路映射

- Date: 2026-04-08
- Phase: Phase 1 - Agent 基础模型
- Debt:
  - Service 层未对数据库底层异常（如 SQLAlchemy 错误）进行精细化拦截和转化，当前依赖全局 500 错误兜底处理。
  - JSONB 序列化当前未配置 `exclude_none=True`，Optional 字段（如 `max_tokens`）可能以 null 的形式写入数据库。
- Impact:
  - 不影响 Phase 1 验收通过（不阻断 API 与契约流转）
  - 可能导致错误日志不够精细，或 JSONB 数据存储体积存在微小冗余。
- Planned Fix Phase:
  - Exception transformation: Phase 8 (API Contracts / Error Handling)
  - Serialization strategy optimization: Deferred / 按需优化
- Status: RESOLVED
- Fix Phase: Phase 8
- Summary: 已通过全局异常处理器统一映射 SQLAlchemyError → DATABASE_ERROR

- Date: 2026-04-09
- Phase: Phase 2 - Model Gateway
- Debt:
  - LimitStatus 未继承 str：当前 LimitStatus 是纯 Enum，若继承 str (class LimitStatus(str, Enum)) 将更便于日志、JSON 序列化和调试。
  - Redis 重连机制可优化：当前 `if not self._redis:` 仅在首次连接时检查，若 Redis client 建立后长期断线，不会自动重建连接。未来生产环境建议在 `ping` 失败后重置 client 并尝试重连。
  - Token 扣减失败静默处理：`add_token_usage` 失败仅记录日志，未向上层抛出错误。对于财务/计费敏感系统，这应标记为“记账最终一致性风险”的技术债。
- Impact:
  - 不影响 Phase 2 验收通过
  - 对后续日志分析、系统稳定性及财务准确性有潜在影响
- Planned Fix Phase:
  - LimitStatus inheritance: Deferred / 按需优化
  - Redis reconnect: Deferred / 运维阶段
  - Token accounting risk: Phase 8 (API Contracts / Error Handling)
- Status: ACCEPTED
- Fix Phase: Phase 8
- Note: 前置 quota 校验已严格生效，扣减失败属于最终一致性问题，当前阶段允许存在

- Date: 2026-04-09
- Phase: Phase 3 - Python Sandbox
- Debt:
  - **弱隔离性风险 (Security Isolation)**: 当前沙箱基于 Python `__builtins__` 安全子集与 OS 进程资源限制 (resource.setrlimit)，属于“弱隔离”。虽然通过 `__builtins__` 限制了危险函数，但仍依赖 OS 层面进行兜底，且未完全阻止文件读写和网络访问。
  - **资源限制 OS 依赖**: `RLIMIT_AS` (内存) 与 `RLIMIT_CPU` (CPU) 在 macOS 上行为不一致或无效，当前实现仅保证 Linux 环境有效。
  - **文件系统隔离不完全**: `RLIMIT_FSIZE=0` 仅限制文件大小，未完全阻止文件读取。
  - **网络隔离缺失**: 未实现真正的网络隔离，仅通过 `__import__` 限制 `socket` 模块，但仍可能存在绕过风险。
- Impact:
  - 不影响 Phase 3 验收通过（已明确为 Route A：弱隔离 + 显式技术债）
  - 对沙箱的安全性、隔离性有潜在风险，不适用于高安全要求的恶意代码执行场景。
- Planned Fix Phase:
  - Containerized Isolation (Docker/gVisor/Firecracker): Phase 10+ / 运维增强阶段

- Date: 2026-04-09
- Phase: Phase 4A (Post-Freeze Improvement)
- Title: ToolResponse ok 字段类型约束增强
- Category: Type Safety / Schema Strictness
- Priority: Low
- Status: Open
- Scope: backend/models/tool.py

- Description:
  当前 Tool Runtime 中的响应模型使用：
  - ToolSuccessResponse: ok: bool = True
  - ToolFailureResponse: ok: bool = False
  
  该实现虽然通过 Field(frozen=True) 固定值，但类型层面仍为 bool，而非严格字面量类型。
  
  建议未来优化为：
  - ok: Literal[True]
  - ok: Literal[False]
  
  以在类型系统层面进一步强化 Success / Failure Envelope 的不可变性与语义确定性。

- Impact:
  - 当前实现已满足所有运行时与结构约束，不影响 Phase 4A Freeze
  - 该问题仅影响类型表达的严谨性，不影响运行结果
  - 不会导致系统错误或不一致行为

- Action:
  - 在未来类型系统优化阶段，将 ok 字段替换为 Literal 类型，并同步更新相关类型提示与校验逻辑。

- Date: 2026-04-10
- Phase: Phase 4.5 - Runtime Integration Audit
- Debt:
  1. Tool Runtime 无法强制 Sandbox 执行
     - 问题描述：Tool Runtime 只负责调用 `tool.execute()`，它无法在架构层面强制所有 Python Tool 必须经过 Sandbox 执行。Sandbox 边界当前依赖具体 Tool 实现自觉遵守。
     - 当前状态：当前已实现的 Python Tool 正确调用了 Sandbox Service，审计通过。
     - 风险：未来新增 Python Tool 若实现不当，可能绕过 Sandbox 直接执行代码，破坏安全边界。
     - 是否阻断当前阶段：NO
     - 建议处理阶段：Phase 5 (Execution Engine) 或后续 Tool Policy / Security Enforcement 阶段

  2. Sandbox error 未统一为 ToolFailureResponse
     - 问题描述：Sandbox 内部执行报错时，当前 `sandbox_service` 会将其映射为 `{"observation": {"error": "..."}}` 的数据形态返回，但在 ToolRuntime 层可能被视为成功响应（ToolSuccessResponse），导致错误未进入 observation.error 字段，而是进入 observation.result。
     - 当前状态：符合当前 Tool Contract，未产生契约冲突，Phase 4.5 审计允许通过。
     - 风险：上层 Execution Engine 在解析时需要额外从 `data.observation` 中提取并判断内部错误，无法统一依赖 `ok=false` 进行失败拦截，增加了解析复杂度。
     - 是否阻断当前阶段：NO
     - 建议处理阶段：Phase 5 (Execution Engine) 适配时确认是否统一错误语义
     - Status: RESOLVED
     - Fix Phase: Phase 6
     - Summary: Tool Runtime 已识别 Sandbox 错误载荷（如 observation.error），并在 success envelope 封装前统一转换为 ToolFailureResponse(ok=false)，同时引入 SANDBOX_ERROR 语义化错误码。Execution Engine 与 Execution Logs 现已可直接复用 ToolFailureResponse 失败路径，无需额外下探 success payload 中的 observation.error。

  3. Tool Registry 为全局单例
     - 问题描述：`ToolRegistry` 当前被设计为全局单例，并在应用启动时通过 `_locked=True` 锁定注册。
     - 当前状态：满足当前静态注册工具的需求。
     - 风险：未来若引入多 Agent、多租户、插件化或动态工具集隔离需求，全局单例将难以支持，并可能带来并发与隔离问题。
     - 是否阻断当前阶段：NO
     - 建议处理阶段：后续多 Agent / 多租户 / 插件化工具系统阶段

  4. request_id 仅用于日志，未形成 tracing
     - 问题描述：HTTP Middleware 注入的 `request_id` 已贯穿 Tool Runtime 并记录到日志中，但尚未与外部分布式 Tracing 系统打通。
     - 当前状态：当前已具备基于日志文本的 request_id 全链路追踪能力。
     - 风险：在更复杂的异步链路、多服务拆分或高并发场景下，仅依赖日志文本追踪排障效率较低，缺乏时序与依赖图能力。
     - 是否阻断当前阶段：NO
     - 建议处理阶段：Phase 6 (Execution Logs / Observability) 或后续可观测性建设阶段

  5. 配置系统优先级实现较脆弱
     - 问题描述：`Settings.load_config()` 当前通过手动过滤 `yaml_data` 实现 `环境变量 > .env > yaml` 的优先级，以避免构造参数覆盖高优先级配置。
     - 当前状态：已修复优先级问题，当前 `DB_URL` 可正确加载。
     - 风险：该实现依赖手动字典键过滤，若未来出现嵌套配置、field alias 或更复杂的配置映射，逻辑可能失效。
     - 是否阻断当前阶段：NO
     - 建议处理阶段：后续 Config System Refactor / Refactoring 阶段

- Date: 2026-04-10 
- Phase: Phase 5 - Execution Engine 
- Debt: 

  1. observation.error 语义未与 ToolFailureResponse 统一 
     - 问题描述：Execution Engine 将所有异常统一转化为 observation.error，但未统一映射为 ToolFailureResponse(ok=false)。 
     - 当前状态：符合当前 Phase 5 contract，审计允许通过。 
     - 风险：上层系统（日志层/API层）需额外解析 observation.error，而非统一依赖 ok=false 判断失败。 
     - 是否阻断当前阶段：NO 
     - 建议处理阶段：Phase 6（Execution Logs）或后续错误语义统一阶段 
     - Status: RESOLVED
     - Fix Phase: Phase 6
     - Summary: 与 Phase 4.5 Debt 2 及 Phase 5.5 Debt 7 一并解决，Runtime 层已能识别 Sandbox 错误并统一转换为 ToolFailureResponse。

  2. Execution Engine 无 memory / context 策略 
     - 问题描述：当前 ReAct 循环仅依赖简单 context 累积，未实现 memory 策略或上下文裁剪机制。 
     - 当前状态：满足最小 ReAct 引擎需求。 
     - 风险：随着 step 增多或输入变复杂，context 可能无限增长，影响模型性能与成本。 
     - 是否阻断当前阶段：NO 
     - 建议处理阶段：Phase 7（Agent / Memory 系统） 

  3. Action 解析完全依赖 LLM 输出规范性 
     - 问题描述：Engine 假设 LLM 输出符合 Action schema，虽然有错误隔离，但没有策略性纠正机制。 
     - 当前状态：非法输出会被转为 observation.error。 
     - 风险：模型持续输出非法结构时，系统可能陷入无效循环直至 max_steps。 
     - 是否阻断当前阶段：NO 
     - 建议处理阶段：Phase 7（Agent 策略层 / Prompt 优化 / Policy 控制） 

  4. 状态机为单实例执行，不支持并发会话隔离 
     - 问题描述：当前 Execution Engine 设计为单次 run 的状态机，未引入 session / 多执行上下文管理。 
     - 当前状态：满足单任务执行。 
     - 风险：未来扩展多 Agent 或并发任务时，缺乏隔离机制。 
     - 是否阻断当前阶段：NO 
     - 建议处理阶段：Phase 7（多 Agent / Session 管理） 

  5. execution_trace 为内存结构，未持久化 
     - 问题描述：执行轨迹仅存在于内存返回结果中，未进行持久化或结构化日志存储。 
     - 当前状态：满足调试与返回需求。 
     - 风险：无法支持审计、回放、分析与监控。 
     - 是否阻断当前阶段：NO 
     - 建议处理阶段：Phase 6（Execution Logs） 
     - Status: RESOLVED
     - Fix Phase: Phase 6
     - Summary: 引入 execution_logs 与 react_steps 双表结构，实现 ReAct Step 全量持久化，支持 execution_id 级别完整回放。

- Date: 2026-04-10 
- Phase: Phase 5.5 - Execution Engine Integration Audit 
- Debt: 

  6. 非法 LLM 输出被映射为 FINISH（隐式成功风险） 
     - 问题描述：当 LLM 输出非法 JSON 或解析失败时，Execution Engine 当前会返回 ActionType.FINISH，并将错误信息写入 final_answer。 
     - 当前状态：系统以 FINISHED 状态结束执行。 
     - 风险：解析失败被误判为成功结束，污染 SUCCESS / ERROR 语义，可能导致上层系统（API / Logs / Monitoring）误判执行结果。 
     - 是否阻断当前阶段：NO 
     - 建议处理阶段：Phase 6（Execution Logs）优先处理 
     - Status: RESOLVED
     - Fix Phase: Phase 6
     - Summary: Parser error 不再映射为 FINISH，非法输出统一进入 error 分支，状态机强制流转为 TERMINATED。

  7. Sandbox 错误未完全进入 observation.error 统一语义 
     - 问题描述：sandbox_service 在部分错误情况下返回结构为 {"observation": {"error": "..."} }，但在 ToolRuntime 层可能被视为成功响应（ToolSuccessResponse），导致错误未进入 observation.error 字段，而是进入 observation.result。 
     - 当前状态：错误信息存在但语义不统一。 
     - 风险：上层系统需要额外判断 result 内容才能识别错误，破坏统一错误处理模型。 
     - 是否阻断当前阶段：NO 
     - 建议处理阶段：Phase 6（Execution Logs）或错误语义统一阶段 
     - Status: RESOLVED
     - Fix Phase: Phase 6
     - Summary: 引入 ExecutionErrorModel 并完成日志层统一收口；同时在 Tool Runtime 层识别 Sandbox 错误载荷并转换为 ToolFailureResponse，使 Runtime / Engine / Logs 三层错误语义保持一致。Sandbox 内部错误不再以 ToolSuccessResponse(ok=true) 形式上漂；后续若需更高层统一错误契约，应作为新债务单独记录，而非保留本条为未完成状态。

- Date: 2026-04-10
- Phase: Phase 6 - Execution Logs
- Debt:

  1. Execution Logs 查询接口缺乏鉴权隔离
     - 问题描述：当前 GET /executions/{execution_id} 未进行用户或团队级权限校验。
     - 当前状态：接口可直接访问 execution 及 react_steps 全量数据。
     - 风险：存在越权访问执行日志的安全风险。
     - 是否阻断当前阶段：NO
     - 建议处理阶段：Phase 8（Auth & Permission）
     - Status: RESOLVED
     - Fix Phase: Phase 8
     - Summary: 已实现 route + service 双层 team_id 过滤

  2. 日志写入在高并发下可能成为瓶颈
     - 问题描述：当前 execution_logs 与 react_steps 采用直接异步数据库写入。
     - 当前状态：满足当前单机与低并发 baseline。
     - 风险：在高并发场景下可能出现数据库写入压力或连接池耗尽。
     - 是否阻断当前阶段：NO
     - 建议处理阶段：Phase 10+（Observability / Queue / Scaling 优化）

- Date: 2026-04-10 
- Phase: Phase 7 - Competition Manager 
- Debt: 
 
   1. Quota 查询未引入缓存层 
      - 问题描述：当前每次请求在 API 层与 Model Gateway 均需访问 DB 查询 TeamQuota 配置。 
      - 当前状态：完全依赖 DB 作为配置源，未引入任何缓存。 
      - 风险：在高并发场景下可能对数据库产生压力。 
      - 是否阻断当前阶段：NO 
      - 建议处理阶段：Phase 10+（Cache / Config Distribution） 
 
   2. Redis usage 未持久化 
      - 问题描述：token_usage 完全存储于 Redis，未同步至数据库。 
      - 当前状态：Redis 作为唯一运行时计数层。 
      - 风险：Redis 数据丢失会导致 usage 重置。 
      - 是否阻断当前阶段：NO 
      - 建议处理阶段：Phase 10+（Usage Persistence / Async Sync） 
 
   3. JWT 权限模型尚未细化 
      - 问题描述：当前仅校验 team_id 与基础合法性，未实现用户级权限控制（RBAC）。 
      - 当前状态：Auth 仅完成 team 维度控制。 
      - 风险：无法进行细粒度权限隔离（如用户级资源访问控制）。 
      - 是否阻断当前阶段：NO 
      - 建议处理阶段：Phase 8（Auth & Permission 扩展） 
      - Status: PARTIALLY_RESOLVED
      - Phase: Phase 8
      - Note: team 级隔离已完成，但 user 级 RBAC 尚未实现，不允许标记为 RESOLVED

- Date: 2026-04-12
- Phase: Phase 9 - 验收收尾（最终审计发现）
- Debt:
   1. LLM 动作解析器与执行引擎存在基于字符串的强耦合
      - 问题描述：`ExecutionEngine._parse_llm_output` 当解析失败时，返回的 `ActionType.FINISH` 对象其 `final_answer` 以 `"Error:"` 开头；外层 `step_execute` 依赖字符串匹配 `startswith("Error:")` 来判断并转入 `TERMINATED`。
      - 当前状态：已存在于代码中。
      - 风险：如果 LLM 合法输出了以 "Error:" 开头的最终答案，将被错误地识别为解析失败并导致引擎 `TERMINATED`。
      - 是否阻断当前阶段：NO
      - 建议处理阶段：Phase 10+（引入独立的 ParserErrorAction 或在解析器内抛出异常进行流转）

- Date: 2026-04-12
- Phase: Phase 9 - Testing & Acceptance
- Title: Execution Engine 错误语义依赖字符串匹配
- Category: Execution Semantics / Engine Design
- Priority: Medium
- Status: OPEN
- Description: 
  当前 Execution Engine 在 _parse_llm_output 解析失败时，会构造 ActionType.FINISH，并在 final_answer 中注入 "Error:" 前缀字符串； 
  随后在执行流程中，通过 .startswith("Error:") 判断是否进入失败终止分支。 
  该实现本质为： 
    - 状态机语义依赖字符串协议 
    - 错误语义未通过结构化字段表达 
    - Engine 与 Parser 存在隐式耦合 
- Risk: 
  - 若 LLM 正常输出文本以 "Error:" 开头，可能被误判为失败 
  - 状态机语义不稳定，存在误终止风险 
  - 不利于后续扩展（如多错误类型 / 多终止原因） 
- Impact: 
  - 当前不影响 Phase 9 测试通过 
  - 不影响 v0.1 交付 
  - 属于设计层隐患 
  - 是否阻断当前阶段：NO 
- 建议处理阶段： 
  - Phase 10+（Execution Engine Refactor） 
- 建议修复方向（仅记录，不允许实现）： 
  - 引入结构化错误类型（如 ActionType.ERROR 或 ExecutionError） 
  - 禁止通过字符串前缀判断状态 
  - 将错误语义纳入状态机显式分支

