# AgentForge Policy Governance Phase Split

This file maps the current workspace changes back to the phase boundaries in
`AgentForge 工具与知识库调用治理全阶段开发方案.md`.

## Phase 1: Classifier And Pre Policy

Suggested commit:

`phase1: add intent classifier and pre-policy gate`

Files:

- `backend/services/tool_need_classifier.py`
- `backend/services/policy_gate.py`
- `backend/services/tool_scope_resolver.py`
- `backend/models/schemas.py`
- `backend/models/constants.py`
- `backend/services/langgraph_execution_strategy.py`
- `tests/unit/test_tool_need_classifier.py`
- `tests/unit/test_pre_policy_gate.py`
- `tests/unit/test_tool_scope_resolver.py`

## Phase 2: Required Knowledge Retrieval

Suggested commit:

`phase2: enforce required knowledge retrieval`

Files:

- `backend/services/retrieval_policy_service.py`
- `backend/services/knowledge_service.py`
- `backend/services/langgraph_execution_strategy.py`
- `tests/unit/test_retrieval_policy_service.py`
- `tests/integration/test_required_knowledge_retrieval.py`

## Phase 3: Clause Parsing And Ranking

Suggested commit:

`phase3: add clause parser and retrieval ranker`

Files:

- `backend/services/knowledge_parser.py`
- `backend/services/knowledge_retrieval_ranker.py`
- `backend/models/orm.py`
- `backend/models/schemas.py`
- `backend/api/routes/knowledge.py`
- `backend/services/knowledge_service.py`
- `tests/unit/test_knowledge_parser.py`
- `tests/unit/test_knowledge_retrieval_ranker.py`
- `tests/unit/test_exact_clause_retrieval.py`

## Phase 4: Tool Risk And Call Gate

Suggested commit:

`phase4: add tool risk metadata and tool policy gate`

Files:

- `plugin_marketplace/interfaces.py`
- `plugin_marketplace/db/models.py`
- `plugin_marketplace/core/registry.py`
- `plugin_marketplace/core/manager.py`
- `plugin_marketplace/adapters/builtin_adapter.py`
- `plugin_marketplace/api/schemas.py`
- `plugin_marketplace/manifests/*.yaml`
- `backend/services/agent_runtime_assembler.py`
- `backend/services/langgraph_execution_strategy.py`
- `backend/services/execution_engine.py`
- `tests/unit/test_plugin_marketplace.py`
- `tests/integration/test_tool_policy_gate.py`

## Phase 5: Final Answer Gate And Observability

Suggested commit:

`phase5: surface policy observability and confirmation UI`

Files:

- `frontend/src/features/execution/*`
- `frontend/src/features/knowledge/knowledge.adapter.ts`
- `frontend/src/components/workspace/chat/ToolConfirmationCard.tsx`
- `frontend/src/components/workspace/layout/CopilotPanel.tsx`
- `frontend/src/components/workspace/builder/pages/PreviewTabPage.tsx`
- `frontend/src/components/workspace/builder/pages/RunLogsTabPage.tsx`
- `frontend/src/components/workspace/builder/pages/KnowledgeTabPage.tsx`
- `frontend/src/pages/LogsPage.tsx`
- `tests/unit/test_final_answer_policy_gate.py`
- `tests/integration/test_final_answer_grounding.py`
- `tests/e2e/test_policy_confirmation_flow.py`

## Phase 6: Eval And CI

Suggested commit:

`phase6: add policy eval and CI coverage`

Files:

- `tests/eval/policy_cases.yaml`
- `tests/eval/test_policy_eval.py`
- `.github/workflows/policy-governance.yml`
- `scripts/migrate_policy_governance.py`
- `backend/services/schema_migration_service.py`
- `backend/main.py`
- `frontend/eslint.config.js`
- `frontend/src/app/routes/index.tsx`
- `frontend/src/app/routes/lazyRoutes.tsx`

## Validation Commands

Backend policy suite:

```bash
PYTHONPATH=. pytest tests/integration/test_execution_engine.py tests/unit/test_tool_need_classifier.py tests/unit/test_pre_policy_gate.py tests/unit/test_retrieval_policy_service.py tests/unit/test_tool_scope_resolver.py tests/unit/test_knowledge_parser.py tests/unit/test_knowledge_retrieval_ranker.py tests/unit/test_exact_clause_retrieval.py tests/unit/test_plugin_marketplace.py tests/unit/test_schema_migration_service.py tests/unit/test_final_answer_policy_gate.py tests/integration/test_required_knowledge_retrieval.py tests/integration/test_tool_policy_gate.py tests/integration/test_policy_inspect_api.py tests/integration/test_final_answer_grounding.py tests/e2e/test_policy_confirmation_flow.py tests/eval/test_policy_eval.py -q
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Migration rehearsal:

```bash
mkdir -p .tmp/policy_migration_rehearsal
cp agentforge_preview.db .tmp/policy_migration_rehearsal/agentforge_preview.migration-test.db
python scripts/migrate_policy_governance.py --database-url sqlite+aiosqlite:///.tmp/policy_migration_rehearsal/agentforge_preview.migration-test.db
```
