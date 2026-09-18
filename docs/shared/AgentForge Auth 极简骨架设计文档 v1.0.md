# AgentForge Auth 极简骨架设计文档 v1.0

**状态：Freeze-Level**
**适用范围：Auth 模块设计与实现阶段**
**角色：SOLO BUILDER / SOLO CODER / SOLO AUDIT**

---

## 1. 架构目标与设计原则

本设计定义 AgentForge 系统的身份认证（Authentication）与访问控制（Authorization）基础骨架，确保执行路径的安全性、单一性与可观测性。

**核心原则：**
* **声明非授权原则**：JWT Claim 仅作为身份声明来源，不等于最终权限，不等于资源访问权。
* **服务端复核原则**：所有资源访问必须由服务端进行归属复核，`team_id` 不能直接作为资源访问依据。
* **职责隔离原则**：AuthContext ≠ Authorization，认证与鉴权严格分层。

---

## 2. Auth 与 AuthZ 边界划分

系统必须严格实现以下三层职责隔离，禁止跨层越权操作：

### 2.1 AuthResolver (Authentication Layer)
* **职责**：身份认证与声明解析。
* **行为**：
  * 解析 HTTP 请求中的身份凭证（如 JWT）。
  * 生成并向下游传递标准 `AuthContext`（包含 `user_id`, `team_id`, `request_id` 等声明信息）。

### 2.2 Authorization Layer (AuthZ Layer)
* **职责**：资源访问控制与权限校验。
* **行为**：
  * 校验 User 是否合法属于声明的 Team。
  * 校验目标资源是否归属于当前 Team。
  * 强制拦截并拒绝任何跨租户（跨 Team）的资源访问请求。

### 2.3 Business / Execution Layer (业务与执行层)
* **职责**：执行核心业务逻辑。
* **行为**：
  * 接收并信任已通过 AuthZ 校验的上下文。
  * **禁止**自行实现鉴权判断逻辑。
  * **禁止**在业务层处理身份解析。

---

## 3. Team-Owned Resource 模型

系统内所有核心业务资源必须遵循 Team-Owned（团队归属）模型。

### 3.1 核心归属资源清单
以下资源默认且必须归属于特定 Team：
* Agent
* Extension Installation
* Tool Binding
* Execution Record
* Execution Artifact
* Runtime State / Quota Context

### 3.2 资源访问约束
* 所有针对上述资源的访问（包含读取、修改、执行、删除等），必须且只能由 Authorization Layer 验证资源归属关系。
* 任何 Agent、Tool 或 Execution 资源的调用，均需将当前上下文中的 `team_id` 与数据库/存储中记录的资源 `team_id` 进行绝对匹配。

---

## 4. 核心组件交互边界

### 4.1 ExecutionEngine 边界约束
ExecutionEngine 作为核心执行引擎，必须遵循无状态执行原则，严禁越界参与鉴权。

* **必须执行**：
  * 接入并全局透传 `AuthContext`。
* **允许执行**：
  * 记录包含 `user_id` / `team_id` / `request_id` 的执行追踪日志。
  * 向 Tool Marketplace 及其底层执行单元透传身份上下文。
* **严禁执行**：
  * 承担任何鉴权职责。
  * 解析 JWT 或任何原始 Token。
  * 校验权限状态。
  * 判断资源的归属关系。

### 4.2 Tool Marketplace 边界约束
* 接收由 ExecutionEngine 透传的 `AuthContext`。
* **严禁**在 Marketplace 内部进行 Token 解析。

---

## 5. 异常与错误码策略

系统必须严格遵守契约不可破坏原则（Contract Freeze），错误码策略不得随意变更。

### 5.1 错误码处理规范
* 必须完全保留现有错误码定义（包含但不限于 5001 / 5002）。
* **禁止**修改现有错误码语义。
* **禁止**删除或合并任何现有错误码。
* 允许前端在开发态统一提示，但后端日志必须精确区分具体错误原因（如 Token 过期、签名错误、格式异常等）。

### 5.2 统一异常出口
* 所有 Auth 与 AuthZ 异常必须由全局异常处理器接管并转换为标准响应结构。
* 不允许局部吞没异常或返回隐式成功。

---

## 6. 日志与可观测性规范

系统必须实现高可追踪性的日志记录，明确各层日志责任。

### 6.1 统一日志字段
所有涉及 Auth/AuthZ 及资源访问的日志，必须包含以下统一字段：
* `request_id`（强制贯穿全局）
* `user_id`
* `team_id`
* `auth_mode`
* `path`
* `resource_type`（针对具体资源操作时必须存在）
* `resource_id`（针对具体资源操作时必须存在）

**安全红线**：任何环境、任何层级的日志中**严禁**打印完整 Token。

### 6.2 日志责任划分
* **AuthResolver 负责**：
  * Auth 入口请求日志。
  * Dev Bypass 命中记录日志。
  * JWT 解析/校验失败日志（需记录失败的具体原因）。
* **Authorization Layer 负责**：
  * Permission Denied（越权/归属校验失败）拦截日志。
* **API / Execution Layer 负责**：
  * Execution Trace（执行链路）追踪日志。
  * Resource Access（资源实际资源读写/调用资源）审计日志。