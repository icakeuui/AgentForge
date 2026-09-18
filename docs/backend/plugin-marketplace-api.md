# Tool Marketplace API

本文档只覆盖 `plugin_marketplace` 模块当前对外暴露的接口，也就是网站端“工具市场”会实际使用到的后端路由。

基础前缀：

- `GET/POST/DELETE http://localhost:8000/api/v1/marketplace/...`

当前状态：

- 本文档中的接口已做自动化测试
- 同时已对 `localhost:8000` 做过真实 HTTP 冒烟验证
- 当前验证基于本地预览后端和 SQLite 预览库

## 1. 列出所有工具扩展

- Method: `GET`
- Path: `/api/v1/marketplace/extensions`
- 用途：工具市场首页拉取全部可展示工具

返回字段要点：

- `id`
- `name`
- `description`
- `tool_type`
- `categories`
- `author`
- `homepage`
- `is_official`
- `config_fields`

## 2. 获取单个扩展详情

- Method: `GET`
- Path: `/api/v1/marketplace/extensions/{extension_id}`
- 用途：进入卡片详情时读取扩展信息和工具列表

当前已验证：

- `builtin` 在未安装前也能返回 `tools`

## 3. 获取扩展下的工具列表

- Method: `GET`
- Path: `/api/v1/marketplace/extensions/{extension_id}/tools`
- 用途：前端展示扩展包含的可绑定工具

当前已验证：

- `builtin` 在未安装前也能返回 `builtin/echo`

## 4. 测试扩展配置

- Method: `POST`
- Path: `/api/v1/marketplace/extensions/{extension_id}/test-connection`
- 用途：用户在页面填完配置后点“Test configuration”

请求体：

```json
{
  "config": {
    "root_path": "D:\\\\workspace"
  }
}
```

返回体：

```json
{
  "ok": true,
  "message": "Configuration looks valid.",
  "missing_fields": []
}
```

当前已验证：

- `filesystem` 非法路径会返回 `ok: false`

## 5. 为用户启用扩展

- Method: `POST`
- Path: `/api/v1/marketplace/extensions/{extension_id}/install`
- 用途：把某个工具扩展启用给指定用户

请求体：

```json
{
  "user_id": "demo-user",
  "config": {}
}
```

返回体：

```json
{
  "extension_id": "builtin",
  "status": "installed",
  "message": "ok"
}
```

## 6. 为用户卸载扩展

- Method: `DELETE`
- Path: `/api/v1/marketplace/extensions/{extension_id}/uninstall`
- Query: `user_id`
- 用途：移除某用户已启用的扩展

示例：

- `/api/v1/marketplace/extensions/builtin/uninstall?user_id=demo-user`

## 7. 查询用户已启用扩展

- Method: `GET`
- Path: `/api/v1/marketplace/users/{user_id}/extensions`
- 用途：页面查看当前用户已经启用的工具扩展

返回字段要点：

- `extension_id`
- `name`
- `description`
- `tool_type`
- `status`
- `error_message`

## 8. 执行工具

- Method: `POST`
- Path: `/api/v1/marketplace/tools/execute`
- 用途：运行某个工具

请求体：

```json
{
  "tool_id": "builtin/echo",
  "arguments": {
    "text": "hello"
  },
  "context": {
    "user_id": "demo-user"
  }
}
```

返回体：

```json
{
  "result": "{\"echo\": \"hello\"}"
}
```

## 9. 获取 Agent 已绑定工具

- Method: `GET`
- Path: `/api/v1/marketplace/agents/{agent_id}/tools`
- 用途：查看某个 Agent 当前可调用的工具

返回格式：

- `tools` 数组
- 每一项是 OpenAI function-calling schema

## 10. 绑定工具到 Agent

- Method: `POST`
- Path: `/api/v1/marketplace/agents/{agent_id}/tools/bind`
- 用途：用户在页面选择工具后绑定到 Agent

请求体：

```json
{
  "tool_ids": ["builtin/echo"]
}
```

返回体：

```json
{
  "status": "ok",
  "agent_id": "demo-agent",
  "bound": 1
}
```

## 11. 从 Agent 解绑工具

- Method: `DELETE`
- Path: `/api/v1/marketplace/agents/{agent_id}/tools/{tool_id}`
- 用途：把某个工具从 Agent 上解绑

示例：

- `/api/v1/marketplace/agents/demo-agent/tools/builtin/echo`

当前已验证：

- 支持 `builtin/echo` 这种带 `/` 的工具 ID

## 12. 获取所有工具 schema

- Method: `GET`
- Path: `/api/v1/marketplace/tools/schemas`
- 用途：给运行时或上层 Agent 编排读取所有函数调用 schema

返回格式：

- `tools` 数组
- 每一项是 OpenAI function-calling schema

## 当前已验证通过的接口集合

下面这些接口已经过真实 HTTP 冒烟验证：

- `GET /api/v1/marketplace/extensions`
- `GET /api/v1/marketplace/extensions/builtin`
- `GET /api/v1/marketplace/extensions/builtin/tools`
- `POST /api/v1/marketplace/extensions/filesystem/test-connection`
- `POST /api/v1/marketplace/extensions/builtin/install`
- `GET /api/v1/marketplace/users/smoke-user/extensions`
- `POST /api/v1/marketplace/agents/smoke-agent/tools/bind`
- `GET /api/v1/marketplace/agents/smoke-agent/tools`
- `GET /api/v1/marketplace/tools/schemas`
- `POST /api/v1/marketplace/tools/execute`
- `DELETE /api/v1/marketplace/agents/smoke-agent/tools/builtin/echo`
- `DELETE /api/v1/marketplace/extensions/builtin/uninstall?user_id=smoke-user`

## 边界说明

- 当前“接口已通”指的是 `plugin_marketplace` 模块本身
- 不代表整个 AgentForge 其他业务接口都做了同等强度的验收
- 当前预览启动使用的是 SQLite 预览库；正式环境仍建议接回 PostgreSQL
