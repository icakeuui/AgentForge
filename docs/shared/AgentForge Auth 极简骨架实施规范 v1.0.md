# AgentForge Auth 极简骨架实施规范 v1.0

**状态：Freeze-Level**
**适用阶段：Auth 模块代码实施阶段**
**适用角色：SOLO CODER / SOLO AUDIT**

---

## 实施目标与核心原则

本规范将《AgentForge Auth 极简骨架设计文档 v1.0》转化为可执行的开发契约。
核心实施目标限定为四项：
1. 保留统一 Authentication 入口。
2. 建立最小 Authorization 校验路径。
3. 为本地开发提供 Dev Bypass 机制。
4. 让 ExecutionEngine、Tool Marketplace 与 Agent API 统一接入 AuthContext。

**严禁行为：** 禁止扩展完整商用 Auth 系统，禁止擅自修改契约与错误码，禁止破坏多租户隔离边界。

---

## 一、实施范围限定

### 1.1 允许实现的范围
* **Authentication 入口标准化**：实现统一的 AuthResolver 依赖，负责解析身份、处理 Dev Bypass、执行 JWT 最小合法性校验、生成 AuthContext 并上抛异常。
* **Authorization 最小骨架**：实现独立的鉴权层，负责校验 User-Team Membership 以及 Team-Owned Resource 的归属权，拒绝跨租户访问。
* **AuthContext 标准化**：将系统中散落的身份信息收敛为标准的 AuthContext 结构向下游传递。
* **日志标准化**：按责任层级补齐安全与追踪日志，强制贯穿 `request_id`。
* **模块接入改造**：改造 Agent API、Tool Marketplace API 与 ExecutionEngine 调用链，使其统一接收并使用 AuthContext。

### 1.2 严禁实现的范围（禁止扩展与破坏）
* **禁止扩展为完整 Auth 系统**：严禁实现 Refresh Token、Redis Session、登录注册、OAuth/OIDC、SSO、RBAC 或细粒度 Scope 权限。
* **禁止修改冻结契约**：严禁修改 5001 / 5002 错误码语义或进行合并；严禁业务层、Marketplace 或 ExecutionEngine 自行解析 Token 或承担鉴权逻辑。
* **禁止匿名化系统**：严禁为开发便利将业务接口匿名化，严禁在业务层硬编码 Dev User/Team 信息。

---

## 二、强制实施顺序

实施必须严格按照以下阶段顺序推进，禁止乱序修改：

### Phase 1：建立 AuthContext 与统一入口
* 定义标准 AuthContext。
* 实现 AuthResolver 统一入口。
* 实现 Dev Bypass 机制。
* 注入 `request_id` 并接通全局异常出口。
* **目标**：所有受保护接口均可通过统一入口获取 AuthContext。

### Phase 2：建立 Authorization 最小骨架
* 实现 User-Team Membership 校验逻辑。
* 实现 Team-Owned Resource 归属校验工具。
* 完善 Permission Denied 异常抛出与日志记录。
* **目标**：保证最小多租户边界成立，强制拒绝跨 Team 访问。

### Phase 3：API 层接入
* 依次改造 Agent API、Tool Marketplace API 及其他受保护 API。
* **目标**：所有资源操作 API 从 AuthContext 获取身份，并经过 Authorization Layer 校验，清除散落的身份读取逻辑。

### Phase 4：Execution 链路接入
* 改造 ExecutionEngine 接收 AuthContext。
* 补全 Execution Trace 日志的身份字段。
* 向 Marketplace 及底层工具执行路径透传身份上下文。
* **目标**：ExecutionEngine 具备身份感知与透传能力，但绝对不承担鉴权职责。

---

## 三、模块实施规范

### 3.1 AuthContext 实施规范
* **必须包含字段**：`user_id`、`team_id`、`auth_mode`、`request_id`。
* **约束**：所有下游模块仅接收 AuthContext 对象，严禁接收或传递裸 Token。不允许各模块自行拼装身份信息。

### 3.2 AuthResolver 实施规范
* **职责**：作为唯一的 Authentication 入口。
* **必须实现**：提取认证信息，判断 Dev Bypass，执行 JWT 最小校验，构造 AuthContext，向上抛出规范异常。
* **禁止**：在路由函数内自行 Decode Token；在服务层重复解析身份；返回松散的字典结构替代标准化对象。

### 3.3 Dev Bypass 实施规范
* **必须实现**：仅限 Local / Development 环境启用。非 Dev 环境若检测到 Bypass 配置，系统启动必须 Fail-Fast。Bypass 命中必须记录专属日志。
* **禁止**：在业务层硬编码身份；运行中静默降级到 Dev 身份；根据客户端请求参数动态切换 Dev 身份。

### 3.4 Authorization Layer 实施规范
* **Membership 校验**：必须校验 User 与 Team 的有效性、从属关系及可用状态。严禁仅凭 JWT Claim 直接放行。
* **Resource 归属校验**：必须覆盖 Agent、Extension Installation、Tool Binding、Execution Record、Execution Artifact、Runtime State / Quota Context。
* **约束**：资源读取、更新、执行、删除必须过归属校验。资源的 `team_id` 必须以服务端存储记录为准，严禁以客户端声明为准。

### 3.5 全局异常处理实施规范
* **必须实现**：统一拦截 Auth 与 AuthZ 异常，输出标准响应结构。
* **约束**：保留 5001 / 5002 语义，明确区分 AuthError、PermissionError 与 BusinessError。严禁局部吞没异常、返回隐式成功或将鉴权失败伪装成普通 500 错误。

### 3.6 日志实施规范
* **AuthResolver 负责**：Auth Entry Log、Dev Bypass Hit Log、JWT Validation Failed Log。
* **Authorization Layer 负责**：Permission Denied Log、Membership Validation Failed Log、Resource Ownership Denied Log。
* **API / Execution Layer 负责**：Execution Trace Log、Resource Access Audit Log。
* **统一约束**：所有受保护链路日志强制包含 `request_id`，并尽可能附带 `user_id` / `team_id` / `auth_mode`。严禁打印完整 Token。

### 3.7 核心业务模块接入规范
* **Agent API**：从 AuthContext 读取身份，所有读写操作必须经过 Authorization Layer 校验，严禁直接信任请求体中的 `team_id`。
* **Tool Marketplace API**：涵盖 Install、Uninstall、Bind、Unbind、Execute、Query 路径，统一接入 AuthContext 并经过 Authorization Layer。内部严禁解析 Token。
* **ExecutionEngine**：接收 AuthContext 并向下游透传，记录相关日志字段。严禁解析 JWT、严禁判断 Membership 或 Resource Ownership、严禁跨请求缓存 AuthContext。

---

## 四、路由接入规则

### 4.1 强制保护接口
凡涉及以下操作的接口，必须挂载 AuthResolver 入口：
* 访问 Team-Owned Resource。
* 调用 Execution。
* 调用 Marketplace（Install / Bind / Execute）。
* 读写 Agent 配置。
* 涉及 Quota 或 Runtime State 的操作。

### 4.2 匿名接口限制
* 仅明确定义为公开能力的接口允许匿名访问。
* 当前业务接口默认全量受保护，Coder 严禁自行扩大匿名接口范围。

---

## 五、验收标准与审计重点

### 5.1 CODER 最低验收标准
1. **统一入口**：受保护接口均通过 AuthResolver 获取上下文，全局无散落的 Token Decode 代码。
2. **Bypass 安全**：Dev Bypass 仅在本地生效，Staging / Production 严格禁用且命中可观测。
3. **租户边界**：Agent / Marketplace / Execution 资源归属校验生效，彻底阻断跨 Team 访问。
4. **引擎纯粹**：ExecutionEngine 完成身份透传，且内部无任何鉴权逻辑。
5. **错误与日志**：5001 / 5002 语义不变，异常分类清晰，核心链路日志 `request_id` 贯穿且无 Token 泄漏。

### 5.2 SOLO AUDIT 审计清单（强制核对）
1. 是否仍存在绕过 AuthResolver 的散落 Token Decode 逻辑？
2. 是否存在业务层或 ExecutionEngine 越权执行鉴权判断？
3. Marketplace 内部是否偷偷包含 Token 解析代码？
4. 是否存在缺失 `request_id` 的受保护链路日志？
5. Dev Bypass 配置是否存在向非 Dev 环境泄漏的风险？
6. 是否存在仅凭 JWT Claim 声明即放行资源访问的漏洞？
7. 所有声明的 Team-Owned Resource 是否已全部接入 Authorization Layer 校验？