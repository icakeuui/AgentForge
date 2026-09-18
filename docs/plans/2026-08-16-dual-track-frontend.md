# Dual Track Frontend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a main entry screen that separates agent development from agent usage through the public square.

**Architecture:** Keep the existing workbench as the development backend, but move it under `/develop/*`. Add a protected home page at `/` with two paths: development and square. Add a public square list backed by a safe public listing endpoint, and route users from square cards to existing `/p/:slug` public trial pages.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic, React Router, React, Vite, Tailwind.

---

### Task 1: Public Square Listing API

**Files:**
- Modify: `backend/models/schemas.py`
- Modify: `backend/services/published_agent_service.py`
- Modify: `backend/api/routes/public_agents.py`
- Test: `tests/integration/test_public_agent_links.py`

**Steps:**
1. Add a failing integration test for `GET /public/agents` returning only active published agents.
2. Run the focused test and confirm it fails with a missing route.
3. Add a public list response model with slug, title, description, opening statement, and avatar URL.
4. Implement service query for active published records and map them through their agent public fields.
5. Re-run focused tests.

### Task 2: Route Restructure

**Files:**
- Modify: `frontend/src/app/routes/index.tsx`
- Modify: `frontend/src/app/routes/lazyRoutes.tsx`
- Modify: `frontend/src/shared/navigation.ts`
- Modify: `frontend/src/components/workspace/layout/WorkspaceRail.tsx`

**Steps:**
1. Make `/` a protected platform home page.
2. Move existing workbench child routes under `/develop`.
3. Redirect legacy `/agents`, `/runs`, `/marketplace`, and `/logs` to their `/develop/*` equivalents.
4. Update internal navigation paths to `/develop/*`.

### Task 3: Home and Square Pages

**Files:**
- Create: `frontend/src/pages/HomePage.tsx`
- Create: `frontend/src/pages/AgentSquarePage.tsx`
- Modify: `frontend/src/features/public-agent/publicAgent.adapter.ts`

**Steps:**
1. Add public square adapter method for `GET /public/agents`.
2. Build the protected home page with two primary actions: 智能体开发 and 智能体广场.
3. Build the square page with published agent cards, loading state, empty state, and open trial action.
4. Keep the public trial page at `/p/:slug`.

### Task 4: Verification

**Steps:**
1. Run `pytest tests/integration/test_public_agent_links.py -v`.
2. Run `npm run build` in `frontend`.
3. Smoke test `/`, `/develop/agents`, `/square`, and `/p/:slug`.
4. Commit changes.
