# AgentForge 后端完整开发阶段规划（FULL DEVELOP PHASE）

版本：v1.0  
状态：执行级开发规范（可直接用于 AI Prompt）  
适用模式：TRAE SOLO（严格 Builder / Coder 分离）  

---

# 一、全局执行规则（最高优先级）

1. 每个 Phase 开始前，必须先阅读指定文档，不允许跳过  
2. 每个 Phase 必须先由 Builder 输出设计与计划，再由 Coder 实现  
3. 严格禁止跨 Phase 开发  
4. 未达到当前 Phase 验收标准，不允许进入下一 Phase  
5. 所有实现必须符合冻结文档，不允许自由发挥  

---

# 二、开发阶段总览

Phase 0：环境与骨架搭建  
Phase 1：Agent 基础模型  
Phase 2：Model Gateway  
Phase 3：Python Sandbox  
Phase 4：Tool Runtime  
Phase 5：Execution Engine（ReAct）  
Phase 6：Execution Logs  
Phase 7：Competition Manager  
Phase 8：API Contracts  
Phase 9：测试与验收闭环  

---

# 三、Phase 0：环境与项目骨架

模式：SOLO CODER  

## 开始前必须阅读

- AGENTFORGE_BACKEND_ARCHITECTURE_SPEC.md  
- AGENTFORGE_CONFIG_AND_ENV_SPEC.md  

## Builder 任务

输出：

- 项目目录结构设计  
- 服务分层结构  
- 配置加载方案  

## Coder 任务

实现：

- FastAPI 项目初始化  
- 基础目录结构（api/services/core/models）  
- config加载（Pydantic Settings）  
- 日志基础结构  

## Baseline

- 项目可启动  
- /health 接口可访问  

## 验收标准

- 项目结构符合架构文档  
- 所有配置通过 .env 加载  
- 无硬编码密钥  

---

# 四、Phase 1：Agent 基础模型

模式：SOLO CODER  

## 开始前必须阅读

- AGENTFORGE_AGENT_CONFIG_CONTRACTS.md  
- AGENTFORGE_DATA_MODELS_AND_DB_SCHEMA_SPEC.md  

## Builder 任务

输出：

- Agent 数据结构  
- 数据库模型设计  

## Coder 任务

实现：

- Agent ORM（SQLAlchemy）  
- Agent CRUD Service  
- 基础存储逻辑  

## Baseline

- 可创建 Agent  

## 验收标准

- Agent 数据符合 contract  
- 所有字段校验有效  
- CRUD 全部可用  

---

# 五、Phase 2：Model Gateway

模式：SOLO CODER  

## 开始前必须阅读

- AGENTFORGE_MODEL_GATEWAY_SPEC.md  
- AGENTFORGE_QUOTA_RATE_LIMIT_AND_BUDGET_SPEC.md  

## Builder 任务

输出：

- Gateway 接口设计  
- 限流与token统计策略  

## Coder 任务

实现：

- chat()统一接口  
- token usage记录  
- rate limit  

## Baseline

- 可调用模型返回结果  

## 验收标准

- 所有模型调用必须通过gateway  
- token usage准确记录  
- 超限正确拒绝  

---

# 六、Phase 3：Python Sandbox

模式：SOLO CODER  

## 开始前必须阅读

- AGENTFORGE_PYTHON_SANDBOX_SECURITY_SPEC.md  

## Builder 任务

输出：

- 沙箱执行策略  
- 安全限制清单  

## Coder 任务

实现：

- Python执行环境  
- 输入输出JSON封装  
- 超时控制  

## Baseline

- 可执行简单Python代码  

## 验收标准

- 禁止文件/网络访问  
- 超时自动终止  
- 输出严格JSON  

---

# 七、Phase 4：Tool Runtime

模式：SOLO CODER  

## 开始前必须阅读

- AGENTFORGE_TOOL_RUNTIME_AND_TOOL_CONTRACTS_SPEC.md  

## Builder 任务

输出：

- Tool 接口规范（ToolDefinition + BaseTool）
- Tool 调用流程（Registry → Executor → Schema校验 → 执行 → 返回）

## Coder 任务

实现：

- Tool 注册机制（ToolRegistry）
- Tool 执行接口（ToolExecutor）
- 输入/输出 Schema 校验机制
- 异常统一封装（error JSON）
- 日志记录（带 request_id）

## Baseline（可验证标准）

1. Tool 注册闭环
- 可注册 Tool
- 可按 name 获取 Tool
- 未注册 Tool 必须抛出受控异常

2. 输入校验强制生效
- 任意非法字段必须被拒绝
- 必须支持 additionalProperties=False

3. 输出校验强制生效
- Tool 输出必须严格符合 output_schema
- 非法输出必须被拦截并转 error

4. 异常隔离
- Tool 内部异常（如 ZeroDivisionError）不得抛出到外层
- 必须转为 {"error": "..."} 返回

5. 日志闭环
- 每次 Tool 执行必须有：
  - start log（带 request_id + input）
  - end log（带 output 或 error）

6. 无隐式行为
系统中不得存在：
- fallback
- retry
- implicit success
- 未校验执行路径

## 验收标准

- 所有 Tool 执行路径必须经过 Schema 校验
- 所有异常必须被捕获并转换为 error JSON
- 日志必须包含 request_id 且完整记录执行前后
- 不得存在未注册 Tool 被执行的路径

# 九、Phase 4.5：Runtime Integration Audit

模式：SOLO BUILDER（AUDIT）

## 开始前必须阅读

- AGENTFORGE_TOOL_RUNTIME_AND_TOOL_CONTRACTS_SPEC.md
- AGENTFORGE_PYTHON_SANDBOX_SECURITY_SPEC.md
- AGENTFORGE_MODEL_GATEWAY_SPEC.md
- Phase 4 Builder 输出
- Phase 4 Coder 实现
- Phase 3 Python Sandbox 实现
- Phase 2 Model Gateway 实现

## Builder 任务

输出：

- Tool Runtime 与 Sandbox 的集成审计结论
- Tool Runtime 与 Gateway 的边界审计结论
- 当前 Runtime 层级边界与调用路径审计报告

## Audit 任务

检查：

1. Tool Runtime 是否保持纯运行时角色
- 不得直接承担 Execution Engine 状态管理
- 不得直接持有业务状态

2. Tool Runtime → Sandbox 调用路径是否清晰
- 涉及 Python 执行的 Tool 是否通过 Sandbox
- 不允许 Tool 直接绕过 Sandbox 执行危险代码

3. Tool Runtime → Gateway 边界是否清晰
- 不允许 Tool Runtime 直接承担模型路由职责
- 所有模型调用必须通过 Model Gateway

4. Schema 校验是否前后闭环
- input_schema 必须在执行前校验
- output_schema 必须在执行后校验
- 非法输入输出必须转为 error JSON

5. 错误隔离是否成立
- Tool / Sandbox / Gateway 错误不得抛出到外层
- 必须转为结构化 error 返回

6. 日志链路是否成立
- request_id 是否贯穿 Tool Runtime / Sandbox / Gateway
- 是否可追踪完整执行路径

## Baseline（可验证标准）

1. 至少一个普通 Tool 可执行成功
2. 至少一个 Python Tool 通过 Sandbox 执行成功
3. 非法 Tool 输入能被 Runtime 拦截
4. Sandbox 错误能被 Tool Runtime 转为 error JSON
5. Gateway 不被 Tool Runtime 越权调用

## 验收标准

- Runtime 层边界清晰，无跨层职责污染
- Tool Runtime / Sandbox / Gateway 调用链可追踪
- 所有 Runtime 级错误均被结构化隔离
- 不存在绕过 Sandbox 或 Gateway 的直接执行路径
- 审计通过后方可进入 Phase 5

---

# 十、Phase 5：Execution Engine（核心）

模式：SOLO BUILDER → SOLO CODER

## 开始前必须阅读

- AGENTFORGE_EXECUTION_ENGINE_REACT_PYTHON_SPEC.md
- AGENTFORGE_AGENT_RUNTIME_STATE_MACHINE_SPEC.md
- AGENTFORGE_TOOL_RUNTIME_AND_TOOL_CONTRACTS_SPEC.md
- AGENTFORGE_MODEL_GATEWAY_SPEC.md
- AGENTFORGE_PYTHON_SANDBOX_SECURITY_SPEC.md
- PHASE_STATUS.md
- TECHNICAL_DEBT.md

## Builder 任务（必须先完成）

输出：

- ReAct 循环流程（Thought → Action → Observation → Loop）
- 状态机设计（State 定义 + 转移条件 + 终止条件）
- Engine 输入输出契约
- step_execute() 输入输出契约
- Thought / Action / Observation 结构定义
- 错误处理策略（所有异常必须转为 observation.error）
- Execution Path（必须符合 Engine → Gateway → Tool Runtime → Sandbox 的调用链）
- 日志与执行记录最小字段定义

必须明确：

1. 最终终止态
- SUCCESS
- MAX_STEPS_REACHED
- ERROR_TERMINATED

2. Action 最小结构
- tool_name
- input_data
- 若为 finish 动作，必须定义 finish 的结构与判定方式

3. Observation 最小结构
- tool_name
- result 或 error
- 必须为结构化 JSON
- 不允许返回未定义结构

4. 非法模型输出处理
- 缺字段
- 非法 tool_name
- 非法 action 类型
- 非 JSON / 非法 schema
- 以上情况必须统一转为 observation.error，不允许直接抛异常

5. 状态机必须显式定义的状态
- INIT
- THINKING
- ACTING
- OBSERVING
- FINISHED
- TERMINATED
- 不允许省略，不允许隐式跳转

禁止：

- 引入 fallback / retry
- 修改 Tool Runtime / Gateway / Sandbox 行为
- 引入隐式状态或全局变量
- 引入多 Agent / Planner / Memory 扩展
- 在 Engine 内直接调用 Sandbox
- 在 Engine 内直接调用 OpenAI / AsyncOpenAI
- 在 Engine 内绕过 Tool Runtime

## Coder 任务

实现：

- run()（完整 Agent 执行入口）
- step_execute()（单步 ReAct 执行）
- ReAct 循环控制（循环调度与终止条件）
- 状态机驱动（严格按状态流转执行）
- max_steps 限制机制
- 非法模型输出兜底处理
- 执行日志记录（至少包含 request_id、step_index、state、action、termination_reason）

实现要求：

1. run()
- 必须负责完整循环调度
- 必须在每一步检查 max_steps
- 必须返回最终结构化执行结果
- 不允许抛出未处理异常

2. step_execute()
- 必须只执行单步
- 必须体现完整 ReAct Step：Thought → Action → Observation
- 不允许承担多步循环职责

3. 状态机
- 所有流转必须显式发生
- 不允许跳跃状态
- 不允许绕过 OBSERVING 直接进入下一轮 THINKING
- 不允许未定义状态

4. 错误处理
- 任意异常（Tool / Gateway / Sandbox / schema / parsing）不得向外抛出
- 必须统一转为 observation.error
- Engine 最终返回中必须可见 termination_reason

5. 边界约束
- 所有模型调用必须通过 Model Gateway
- 所有工具调用必须通过 Tool Runtime
- Python Tool 如涉及执行，必须沿现有 Tool Runtime → Sandbox 链路运行
- 不允许跨层直接调用

## Baseline（可验证标准）

1. 单步执行闭环
- 可完成一次完整 ReAct Step（Thought → Action → Observation）
- Observation 必须为结构化 JSON

2. 循环控制生效
- run() 可驱动多步 ReAct 循环
- max_steps 达到后必须终止执行

3. 状态机强约束
- 每一步执行必须由状态机驱动
- 不允许跳跃状态或绕过状态流转

4. 错误隔离
- 任意异常（Tool / Gateway / Sandbox / schema / parsing）不得抛出
- 必须转为 observation.error

5. 调用链一致性
- 所有模型调用必须通过 Model Gateway
- 所有工具调用必须通过 Tool Runtime
- 不允许跨层直接调用

6. 无隐式行为
系统中不得存在：
- fallback
- retry
- implicit success
- 未定义状态流转
- 未记录执行路径

7. 最终结果可判定
- run() 必须返回明确的 final_state
- 必须返回 steps_used
- 必须返回 termination_reason
- 必须返回完整或最小必要的 execution trace

## 验收标准

- 完整 ReAct 循环可运行（至少 2 step）
- max_steps 限制严格生效
- 状态机流转严格符合定义（无非法跳转）
- 所有错误均被转换为 observation.error
- 日志中可追踪完整执行链（包含 request_id）
- Engine 最终返回结构明确，能够区分 SUCCESS / MAX_STEPS_REACHED / ERROR_TERMINATED
# 十一、Phase 5.5：Engine Integration Audit

模式：SOLO BUILDER（AUDIT）

## 开始前必须阅读

- AGENTFORGE_EXECUTION_ENGINE_REACT_PYTHON_SPEC.md
- AGENTFORGE_AGENT_RUNTIME_STATE_MACHINE_SPEC.md
- AGENTFORGE_TOOL_RUNTIME_AND_TOOL_CONTRACTS_SPEC.md
- AGENTFORGE_MODEL_GATEWAY_SPEC.md
- AGENTFORGE_PYTHON_SANDBOX_SECURITY_SPEC.md
- Phase 5 Builder 输出
- Phase 5 Coder 实现
- Phase 4 Runtime 实现
- Phase 3 Sandbox 实现
- Phase 2 Gateway 实现

## Builder 任务

输出：

- Execution Engine 集成审计结论
- State Machine 审计结论
- 调用链一致性审计报告

## Audit 任务

检查：

1. Engine 是否严格基于状态机运行
- 不允许无状态跃迁
- 不允许跳步执行

2. ReAct 循环是否完整
- Thought → Action → Observation 是否完整闭环
- 是否支持多步循环
- 是否严格受 max_steps 约束

3. 调用链是否固定
- Engine → Gateway
- Engine → Tool Runtime
- Tool Runtime → Sandbox
- 不允许出现跨层直调

4. Observation 语义是否统一
- Tool / Gateway / Sandbox 返回是否统一映射为 observation
- 错误是否统一映射为 observation.error

5. 错误是否完全隔离
- 不允许未捕获异常泄漏到上层 API
- 不允许 Engine 因单步失败崩溃

6. 执行日志前置条件是否满足
- 每一步是否具备被日志系统接管的必要字段
- request_id 是否可贯穿整个执行过程

## Baseline（可验证标准）

1. 一个最小 Agent 可完成至少 2 步 ReAct 执行
2. 工具失败不会导致 Engine 崩溃
3. 模型失败不会导致状态机错乱
4. 超过 max_steps 时执行正确结束
5. Engine 可输出完整 step 级执行结果

## 验收标准

- Execution Engine 行为正确且调用链固定
- 状态机无非法跳转
- 所有子系统错误均被吸收为 observation.error
- Engine 已具备接入 Execution Logs 的条件
- 审计通过后方可进入 Phase 6

---

# 十二、Phase 6：Execution Logs

模式：SOLO BUILDER → SOLO CODER

## 开始前必须阅读

- AGENTFORGE_EXECUTION_LOGGING_AND_AUDIT_SPEC.md
- AGENTFORGE_AGENT_RUNTIME_STATE_MACHINE_SPEC.md
- AGENTFORGE_EXECUTION_ENGINE_REACT_PYTHON_SPEC.md
- AGENTFORGE_API_CONTRACTS.md
- PHASE_STATUS.md
- TECHNICAL_DEBT.md

## Builder 任务

输出：

- execution_logs / react_steps 数据结构设计
- execution 级 / step 级日志字段定义
- execution_id / request_id / agent_id / step_index 的关系设计
- 日志写入时机设计
- 最小回放路径设计
- 审计字段（audit fields）设计
- 统一错误语义字段设计（ExecutionErrorModel / Error Semantics）

必须明确：

1. execution_logs 主记录字段
- execution_id
- request_id
- agent_id
- final_state
- termination_reason
- status
- started_at
- completed_at
- steps_used
- final_answer（如有）
- error_code（如有）
- error_source（如有）
- error_message（如有）

2. react_steps 字段
- execution_id
- step_index
- request_id
- state_before
- state_after
- thought
- action
- observation
- step_status
- error_code（如有）
- error_source（如有）
- error_message（如有）
- created_at

3. 状态区分
- success
- failed
- timeout
- cancelled
- max_steps_reached
必须明确这些状态的来源与映射规则

4. 最小回放定义
- 可按 execution_id 查询完整 execution
- 可恢复所有 step 的顺序
- 可恢复 Thought / Action / Observation
- 可恢复 final_state 与 termination_reason

5. 统一错误语义
必须设计统一错误字段，解决以下问题：
- observation.error
- ToolFailureResponse
- sandbox error
- gateway error
- 解析错误
日志层必须能统一表达这些错误，不允许错误语义散落在不同字段且无法归并

禁止：

- 修改 Execution Engine 核心状态机
- 修改 Tool Runtime / Gateway / Sandbox 边界
- 把日志层实现成新的执行引擎
- 引入 fallback / retry
- 引入隐式日志写入行为
- 在执行完成后一次性补写所有日志

## Coder 任务

实现：

- execution_logs 表
- react_steps 表
- execution 级与 step 级日志写入
- 日志查询基础能力
- 最小回放基础能力
- 统一错误语义的日志映射字段

实现要求：

1. execution start 时必须写入 execution_logs 初始记录
2. 每个 ReAct step 完成后必须写入 react_steps
3. execution 结束时必须更新 execution_logs 最终状态
4. 即使执行失败、异常终止、max_steps 截断，也必须保留完整日志
5. 不允许出现“执行成功但无日志”或“执行失败但无日志”的路径
6. 不允许通过修改 Engine 核心业务逻辑来规避日志设计问题
7. 日志写入必须与 execution_id 绑定
8. react_steps 必须支持按 execution_id + step_index 顺序查询

## Baseline（可验证标准）

1. 每次 Agent 执行必须产生 execution 级日志
2. 每个 ReAct step 必须产生 step 级日志
3. 日志必须包含 request_id / execution_id / agent_id
4. 错误执行也必须有完整日志
5. 日志数据可支持最小回放
6. 日志中必须能统一表达错误来源与错误语义
7. 不允许出现 success / failed / timeout / cancelled / max_steps_reached 混淆

## 验收标准

- 全链路执行可回放
- 所有核心字段完整记录
- 日志中可区分 success / failed / timeout / cancelled / max_steps_reached
- react_steps 可完整追踪 Thought / Action / Observation
- execution_logs 与 react_steps 关联清晰
- 错误语义在日志层统一可查询
- 不允许出现“执行成功但无日志”或“失败无日志”的路径
---

# 十三、Phase 7：Competition Manager

模式：SOLO BUILDER → SOLO CODER

## 开始前必须阅读

- AGENTFORGE_COMPETITION_MANAGER_SPEC.md
- AGENTFORGE_QUOTA_RATE_LIMIT_AND_BUDGET_SPEC.md
- AGENTFORGE_AUTH_AND_PERMISSION_SPEC.md
- AGENTFORGE_MODEL_GATEWAY_SPEC.md
- AGENTFORGE_API_CONTRACTS.md
- PHASE_STATUS.md
- TECHNICAL_DEBT.md

## Builder 任务

输出：

- 比赛配置模型
- team / quota / permission 关系模型
- 配额控制路径与拒绝策略
- team quota 状态查询模型

必须明确：

1. `team_id` 为正式执行路径强制上下文
- 不允许隐式默认 `team_id`
- 无 team 或无权限上下文时，必须在进入正式执行路径前拒绝

2. quota 至少区分两类
- token_limit
- rate_limit

3. quota 检查时机
- 必须在正式模型调用前完成 team 配额校验
- 不允许先执行后补扣
- 不允许超限后继续调用

4. 拒绝策略
- team 超限必须返回结构化错误
- 错误码必须与现有 Gateway / 全局错误处理规范一致
- 不允许只抛裸异常字符串

5. team quota 状态查询最小字段
- team_id
- token_limit
- token_used
- rate_limit
- 当前使用状态
- quota_status

6. 边界约束
- Competition Manager 仅作为比赛控制层 / 配额控制层
- 不负责改写 Execution Engine 状态机
- 不直接承担模型调用
- 必须通过 Gateway 联动 team 配额逻辑

## Coder 任务

实现：

- team 管理
- team_id 绑定
- token_limit / rate_limit 管理
- Competition Manager 基础服务
- 与 Gateway 的 team 配额联动
- team quota 状态查询基础能力

## Baseline（可验证标准）

1. 系统可识别 team 维度主体
2. 不同 team 的配额隔离生效
3. team 超限后调用立即被拒绝
4. team 配额状态可查询
5. 无 team 或无权限上下文时不得进入正式执行路径
6. 不允许使用隐式默认 team_id
7. team 超限拒绝必须为结构化错误响应

## 验收标准

- 超限拒绝执行
- 配额严格按 team 生效
- 配额逻辑与 Model Gateway 一致
- 不允许跨 team 污染 token 统计
- Competition Manager 可作为比赛控制层独立工作
- team quota 状态查询结果完整且可审计

# 十四、Phase 8：API Contracts

模式：SOLO BUILDER → SOLO CODER

## 开始前必须阅读

- AGENTFORGE_API_CONTRACTS.md
- AGENTFORGE_ERROR_CODE_AND_FAILURE_HANDLING_SPEC.md
- AGENTFORGE_AUTH_AND_PERMISSION_SPEC.md
- PHASE_STATUS.md
- TECHNICAL_DEBT.md

---

## Builder 任务

输出：

- API schema
- 请求/响应 contract
- error code 映射规则
- 认证与权限约束
- 资源访问控制规则
- 全局异常出口规则

---

### 必须明确

#### 1. 所有对外接口统一响应结构

- 成功与失败均必须遵循统一 contract
- 不允许任意接口私自返回裸 dict、裸字符串或框架默认错误页

#### 2. 所有错误必须映射到冻结错误码

必须覆盖：

- 鉴权失败
- 权限失败
- 资源不存在
- 参数校验失败
- quota / rate limit
- model / tool / sandbox / engine / internal error

补充约束：

- 不允许遗漏映射
- 不允许多个语义复用同一错误码导致冲突
- 不允许将所有错误压缩为单一“通用错误”（必须保留语义粒度）

---

#### 3. HTTP Status 与业务 Code 必须分离

必须同时满足：

- HTTP Status 表达协议层语义
- ResponseCode 表达业务语义

标准映射要求：

- 401 → AUTH_REQUIRED / TOKEN_INVALID / TOKEN_EXPIRED
- 403 → PERMISSION_DENIED / TEAM_FORBIDDEN
- 404 → NOT_FOUND
- 422 → VALIDATION_ERROR
- 429 → QUOTA_EXCEEDED / RATE_LIMIT_EXCEEDED
- 500 → INTERNAL_ERROR / ENGINE_ERROR / MODEL_ERROR 等

禁止：

- 仅返回 HTTP Status
- 或仅返回业务 code
- 或混用导致语义不一致

---

#### 4. 认证与权限约束必须统一接入

- 所有正式接口必须经过鉴权
- 所有 team 相关资源必须经过权限校验
- 日志与执行查询接口必须补齐鉴权与权限校验
- 不允许存在“知道 execution_id 或 team_id 即可直接读取数据”的路径

---

#### 5. 全局异常处理器必须成为唯一未受控异常出口

- 不允许接口层绕过全局异常处理器
- 不允许局部随意返回未统一格式的异常响应
- 不允许暴露底层异常细节给外部调用方

---

#### 6. 本阶段需要顺带收口的技术债务

- Phase 0：错误码最小集合需与冻结错误规范全面对齐
- Phase 1：数据库底层异常需精细化拦截并映射
- Phase 6：Execution Logs 查询接口缺乏鉴权隔离
- Phase 7：JWT 权限模型尚未细化到用户级资源访问控制
- Phase 2：Token 扣减失败静默处理，需明确对外 contract 与内部处理边界

---

#### 7. 本阶段不处理的内容

- Memory / Context 策略
- Action parsing 策略优化
- 多 Session / 多 Agent 隔离
- Redis 重连优化
- 沙箱容器化隔离
- 高并发缓存层 / usage 持久化 / 队列化
- Tool Runtime 强制 Sandbox enforcement
- 类型系统增强（如 Literal[True/False]）

---

## Coder 任务

实现：

- 所有对外接口
- 统一响应结构
- 错误码系统
- 全局异常映射
- 鉴权与权限校验接入
- execution / team / agent 等资源访问控制
- API 与内部执行链对齐
- 数据库异常到标准错误响应的映射
- execution 查询接口鉴权补齐
- Token accounting failure 的 contract 处理边界

---

## API Contract 要求

#### 1. 统一成功响应结构

- { code, message, data }

#### 2. 统一失败响应结构

- { code, message, data }
- data 可为空或承载最小必要上下文
- 不允许出现不受控字段漂移

#### 3. 请求 schema 必须显式定义

- 所有接口输入使用明确 schema
- 不允许隐式参数、未声明字段、模糊 body 结构

#### 4. 响应 schema 必须显式定义

- 所有接口必须有明确 response model 或等价契约约束
- 不允许“返回什么算什么”

---

## 错误码映射规则

必须输出并实现明确映射，至少覆盖：

### 1. 鉴权类

- AUTH_REQUIRED
- TOKEN_INVALID / 等价冻结错误码
- TOKEN_EXPIRED / 等价冻结错误码

---

### 2. 权限类

- PERMISSION_DENIED / 等价冻结错误码
- TEAM_FORBIDDEN / 等价冻结错误码

---

### 3. 资源类

- NOT_FOUND

补充约束：

- NOT_FOUND 必须保留独立语义
- 不允许归并到 INTERNAL_ERROR 或通用错误

---

### 4. 校验类

- VALIDATION_ERROR

补充约束：

- 参数错误必须独立映射
- 不允许与 NOT_FOUND 或 INTERNAL_ERROR 混用

---

### 5. 配额类

- QUOTA_EXCEEDED
- RATE_LIMIT_EXCEEDED

---

### 6. 内部执行链类

- MODEL_ERROR
- MODEL_TIMEOUT
- TOOL_ERROR
- SANDBOX_ERROR
- ENGINE_ERROR
- INTERNAL_ERROR

---

### 映射总约束

- 所有错误码与冻结规范对齐
- 不允许新增未审计错误码
- 不允许语义冲突
- 不允许“一个错误码覆盖多类错误语义”

---

## 认证与权限约束

#### 1. 所有正式接口必须鉴权

- 无 token → 401
- token 无效 → 401
- token 过期 → 401

---

#### 2. 所有 team 相关资源必须校验权限

- 用户只能访问自己有权限的 team
- 不允许仅凭 team_id 读取 quota / execution / agent 结果

---

#### 3. 所有 execution 查询接口必须补齐鉴权

- execution_id 不可作为公开访问凭据
- 必须校验其所属 team / user 权限

---

#### 4. team 与 user 权限分层

- team：资源隔离边界
- user：访问控制主体
- 不允许混淆或互相替代

---

## 全局异常处理要求

1. 所有未受控异常必须进入全局异常处理器  
2. 所有对外错误响应必须统一格式  
3. 禁止直接暴露数据库错误、堆栈、第三方异常明文  
4. 局部 handler 仅可做受控转换，不可绕过统一 contract  

---

## Baseline（可验证标准）

1. 所有接口均可调用  
2. 所有返回结构统一为 contract 规定格式  
3. 所有错误均映射到冻结错误码  
4. 所有鉴权失败 / 权限失败均返回受控错误  
5. 不允许接口绕过全局异常处理器  
6. execution 查询接口已补齐鉴权与权限校验  
7. 数据库底层异常已进行受控映射，不再仅依赖裸 500  
8. Token accounting failure 至少具备明确的内部记录与对外 contract 边界  

---

## 验收标准

- 返回结构统一  
- 错误码完整且无冲突  
- 鉴权与权限逻辑生效  
- execution / team / agent 访问控制生效  
- 不存在未受控异常出口  
- 所有 API 与后端内部执行链一致对齐  
- 技术债务中属于 Phase 8 范围的条目完成收口或明确边界

# 十五、Phase 9：测试与验收闭环

模式：SOLO BUILDER → SOLO CODER  

## 开始前必须阅读

- AGENTFORGE_TESTING_AND_ACCEPTANCE_SPEC.md
- AGENTFORGE_V0_1_DELIVERY_CHECKLIST.md
- PHASE_STATUS.md
- TECHNICAL_DEBT.md

## Builder 任务

输出：

- 测试计划
- 单元 / 集成 / E2E 测试矩阵
- FAIL 路径断言清单
- 最终验收路径
- 一键验收脚本设计

必须明确：

1. 单元测试范围
- schemas / constants / exceptions
- tool runtime
- sandbox service
- rate limiter
- competition manager
- auth dependencies
- response contract

2. 集成测试范围
- API + DB
- API + Auth + Permission
- Execution Engine → Model Gateway → Tool Runtime
- Execution Logs 查询与 team 隔离
- quota / rate limit 生效路径

3. E2E 测试范围
- Agent 创建 → 执行 → 日志回放完整闭环
- Competition 配额生效
- API contract 全量校验
- 关键失败路径闭环

4. FAIL 路径必须覆盖
- JWT 缺失 / 无效 / 过期
- team 越权
- execution 越权查询
- quota exhausted
- rate limit exceeded
- sandbox error
- tool error
- model timeout / model error
- 非法 LLM 输出
- validation error
- database error 映射

5. 一键验收产物
- 必须提供统一验收脚本
- 必须输出：
  - 单元测试结果
  - 集成测试结果
  - E2E 测试结果
  - 最终 PASS / FAIL

6. 本阶段不处理
- 性能压测
- 分布式测试
- 前端联调
- 运维监控建设
- 高并发与扩缩容验证

## Coder 任务

实现：

- 单元测试
- 集成测试
- E2E 测试
- FAIL 路径错误断言
- 交付前最终验收脚本

## Baseline（可验证标准）

1. 核心模块均有单元测试
2. 关键链路有集成测试
3. Agent 主链路有 E2E 测试
4. 所有 FAIL 路径有错误断言
5. 交付前可一键执行验收

## 最终后端闭环验收标准（必须全部满足）

1. Agent 创建 → 执行 → 日志 完整闭环
2. ReAct 执行稳定运行
3. Python Sandbox 在 v0.1 范围内安全可控
4. Tool 调用完整可用
5. Model Gateway 限流与统计正确
6. Competition 配额生效
7. API 全部符合 contract
8. 日志可完整回放
9. 无未捕获异常
10. 所有测试通过

## 验收标准

- 单元 / 集成 / E2E 测试全部通过
- 最终交付脚本可复现实验结果
- 所有模块满足 Delivery Checklist
- 系统达到 v0.1 后端闭环交付标准
---

# 十六、最终执行约束

1. 不允许跳 Phase
2. 不允许合并 Phase 开发
3. Builder 未输出设计不得编码
4. Audit 未通过不得进入下一 Phase
5. 所有实现必须严格符合 Spec
6. 任何偏离必须回退
7. 技术债必须显式记录，不得隐式带入下一 Phase

# 结论

本文件为 AgentForge 后端完整开发执行规范，可直接作为 TRAE SOLO Prompt 使用，驱动 AI 按阶段完成系统构建并确保最终形成稳定后端闭环。