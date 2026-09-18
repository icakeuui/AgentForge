# Plugin Marketplace

Independent plugin marketplace and tool-extension module for AgentForge.

## What This Module Owns

- extension catalog and manifest loading
- install and uninstall lifecycle
- tool registry persistence
- agent-tool binding
- builtin, MCP, and API adapter execution paths
- marketplace HTTP routes

## Host Integration Steps

1. Install backend dependencies from `backend/requirements.txt`
2. Create marketplace tables with `plugin_marketplace.db.database.init_db(engine)`
3. Initialize `MarketplaceAPI`
4. Attach the instance to `app.state.pm_api`
5. Mount `plugin_marketplace.api.routes.create_router()`

## Minimal Host Wiring

```python
from plugin_marketplace import MarketplaceAPI
from plugin_marketplace.api.routes import create_router
from plugin_marketplace.db.database import init_db as init_pm_db

await init_pm_db(engine)
pm_api = MarketplaceAPI(database_url=settings.DB_URL, session_factory=AsyncSessionLocal)
await pm_api.initialize()
app.state.pm_api = pm_api
app.include_router(create_router())
```

## Runtime Calls

- `await pm_api.execute_tool(tool_id, arguments, context)`
- `await pm_api.get_tools_for_agent(agent_id)`
- `await pm_api.install_extension(extension_id, user_id, config)`
- `await pm_api.uninstall_extension(extension_id, user_id)`

## Standalone Verification

Run:

```bash
python run_pm_test.py
python -m pytest tests/unit/test_plugin_marketplace.py -q --noconftest
python -m pytest tests/unit/test_plugin_marketplace_bindings.py -q --noconftest
python -m pytest tests/unit/test_plugin_marketplace_adapters.py -q --noconftest
```
