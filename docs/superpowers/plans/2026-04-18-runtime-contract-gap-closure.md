# Runtime 契约缺口收口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐 `prompt-templates` API 文档、落地 `/api/search` 与 `/api/bootstrap` 后端接口、清理前端孤儿 Runtime wrapper，并同步测试与契约文档。

**Architecture:** 本轮只处理“代码已存在但文档漏记”“前端 wrapper 与后端路由失配”“文档声明已覆盖但后端未落地”三类缺口。后端继续沿用 `routes -> services -> repositories` 分层；前端优先删除未被页面消费且当前无真实后端契约支撑的孤儿 wrapper；文档以当前真实代码为准同步回写。

**Tech Stack:** FastAPI + SQLAlchemy + pytest + Vue 3 + TypeScript + Vitest + Markdown

---

## 范围

- 必做：
  - 为 `/api/prompt-templates` 补齐唯一 API 文档。
  - 新增 `/api/bootstrap` 与 `/api/search` 后端真实路由，并接入 app factory。
  - 清理 `runtime-client.ts` 中当前无真实后端或无前端消费的孤儿 wrapper。
  - 同步补 runtime tests、contract tests、desktop runtime-client tests、API 文档。
- 不做：
  - 不扩展 16 页之外的新页面。
  - 不引入假数据冒充真实后端。
  - 不重做 M10-M15 已有业务流，只做契约收口。

## 顺序任务

### Task 1: 后端补齐 `/api/bootstrap` 与 `/api/search`

**Files:**
- Create: `apps/py-runtime/src/api/routes/bootstrap.py`
- Create: `apps/py-runtime/src/api/routes/search.py`
- Create if needed: `apps/py-runtime/src/schemas/bootstrap.py`
- Create if needed: `apps/py-runtime/src/schemas/search.py`
- Create if needed: `apps/py-runtime/src/services/bootstrap_service.py`
- Create if needed: `apps/py-runtime/src/services/search_service.py`
- Modify: `apps/py-runtime/src/api/routes/__init__.py`
- Modify: `apps/py-runtime/src/app/factory.py`
- Test: `tests/runtime/test_bootstrap_routes.py`
- Test: `tests/runtime/test_search_service.py`
- Test: `tests/contracts/test_bootstrap_contract.py`
- Test: `tests/contracts/test_search_contract.py`

- [ ] 先写后端 failing tests，覆盖成功信封、关键字段、404/422/500 边界。
- [ ] 运行新增测试，确认先红。
- [ ] 写最小后端实现，让测试转绿。
- [ ] 跑新增测试与相关回归测试。

### Task 2: 前端清理孤儿 Runtime wrapper 与契约测试

**Files:**
- Modify: `apps/desktop/src/app/runtime-client.ts`
- Modify if needed: `apps/desktop/src/types/runtime.ts`
- Modify: `apps/desktop/tests/runtime-client-m09-m15.spec.ts`
- Modify if needed: `apps/desktop/tests/runtime-client-settings.spec.ts`
- Modify if needed: `apps/desktop/tests/runtime-client-b-s5.spec.ts`

- [ ] 先写或更新 failing tests，锁定保留的真实 wrapper 与要删除的孤儿 wrapper。
- [ ] 运行前端相关测试，确认先红。
- [ ] 删除或改写孤儿 wrapper，保证仅保留真实后端契约。
- [ ] 跑相关 Vitest 用例，确认转绿。

### Task 3: API 文档与契约文档回写

**Files:**
- Modify: `docs/RUNTIME-API-CALLS.md`
- Modify if needed: `docs/PROJECT-STATUS.md`

- [ ] 将 `/api/prompt-templates`、`/api/bootstrap`、`/api/search` 写入文档。
- [ ] 回写孤儿 wrapper 清理后的真实前端调用点。
- [ ] 删除过时的“已覆盖但未落地”表述。
- [ ] 最后跑一轮相关测试，确保文档与代码一致。

## 验证

- 后端最少验证：
  - `pytest tests/runtime/test_bootstrap_routes.py tests/runtime/test_search_service.py tests/contracts/test_bootstrap_contract.py tests/contracts/test_search_contract.py -q`
- 前端最少验证：
  - `npm --prefix apps/desktop run vitest -- run apps/desktop/tests/runtime-client-m09-m15.spec.ts apps/desktop/tests/runtime-client-b-s5.spec.ts`
- 若改动触达工厂或路由装配，追加：
  - `pytest tests/contracts/test_runtime_page_modules_contract.py tests/contracts/test_runtime_health_contract.py tests/contracts/test_tasks_contract.py -q`

