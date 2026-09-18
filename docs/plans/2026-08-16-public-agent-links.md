# Public Agent Links Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Publish a configured AgentForge agent as a public, runnable chat page link.

**Architecture:** Add a `published_agents` table linked to existing agents and teams. Protected endpoints manage publication, while public endpoints resolve a slug and execute the published agent without exposing admin data or model credentials. The frontend adds a compact publishing panel in the agent config surface and a standalone `/p/:slug` chat page.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic, SQLite, React, Vite, Zustand, Tailwind.

---

### Task 1: Backend Publication Contract

**Files:**
- Modify: `backend/models/orm.py`
- Modify: `backend/models/schemas.py`
- Create: `backend/services/published_agent_service.py`
- Create: `tests/integration/test_public_agent_links.py`

**Steps:**
1. Write failing tests for publishing an owned agent, reading the public profile, disabling a publication, and rejecting disabled slugs.
2. Run `pytest tests/integration/test_public_agent_links.py -v` and confirm the missing route/model failures.
3. Add `PublishedAgent` ORM model and Pydantic request/response models.
4. Implement a service that creates unique slugs, upserts publication records, reads active public records, and disables records.
5. Re-run the focused tests until these contract tests pass.

### Task 2: Protected and Public API Routes

**Files:**
- Modify: `backend/api/routes/agents.py`
- Create: `backend/api/routes/public_agents.py`
- Modify: `backend/main.py`
- Test: `tests/integration/test_public_agent_links.py`

**Steps:**
1. Extend tests to call `POST /agents/{id}/publish`, `GET /agents/{id}/publish`, `PATCH /agents/{id}/publish`, `DELETE /agents/{id}/publish`, `GET /public/agents/{slug}`, and `POST /public/agents/{slug}/execute`.
2. Verify tests fail because routes are absent.
3. Add protected publication endpoints that reuse existing ownership checks.
4. Add public endpoints that never require login and only return public-safe fields.
5. Public execute should reuse existing execution engine flow with the publication team context and return an `execution_id`.
6. Re-run focused tests and fix only behavior covered by those tests.

### Task 3: Frontend Publishing UI

**Files:**
- Modify: `frontend/src/features/agent/agent.adapter.ts`
- Modify: `frontend/src/components/workspace/builder/pages/AgentConfigTabPage.tsx`
- Create: `frontend/src/features/public-agent/publicAgent.adapter.ts`
- Create: `frontend/src/pages/PublicAgentPage.tsx`
- Modify: `frontend/src/app/routes/lazyRoutes.tsx`
- Modify: `frontend/src/app/routes/index.tsx`

**Steps:**
1. Add typed adapter functions for protected publication management and public agent chat calls.
2. Add a publish panel to the edit-mode agent config sidebar: publish, copy link, disable, re-enable, and status display.
3. Add `/p/:slug` route outside the protected app shell.
4. Build a focused public chat page with title, description, conversation transcript, input, loading, and error states.
5. Keep styling consistent with the existing app shell while making the public page self-contained.

### Task 4: Verification

**Files:**
- Existing backend and frontend test/build commands.

**Steps:**
1. Run `pytest tests/integration/test_public_agent_links.py -v`.
2. Run a broader backend smoke set if focused tests pass.
3. Run `npm run build` in `frontend`.
4. Start the local stack or use the already running stack, then manually verify a publish link opens and the public profile loads.
5. Commit the feature branch after all required checks pass.
