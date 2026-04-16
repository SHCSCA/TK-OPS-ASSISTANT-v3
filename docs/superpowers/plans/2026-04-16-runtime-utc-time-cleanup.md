# Runtime UTC Time Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 清理 Runtime 中 `datetime.utcnow()` 弃用警告，统一使用 timezone-aware UTC 时间，保证后续 M07/M09-M15 验证不再被弃用警告污染。

**Architecture:** 新增一个轻量共享时间工具，集中提供 `utc_now()` 和 `utc_now_iso()`。DateTime 字段使用 timezone-aware `datetime`，字符串时间字段使用统一 `Z` 后缀 ISO 格式，避免各 repository/service 自己拼接时间。

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, Pytest, SQLite Runtime。

---

## Status

2026-04-16 已完成并通过验收。Runtime 已统一使用 timezone-aware UTC 时间工具，`apps/py-runtime/src` 下已无 `datetime.utcnow(`；桌面状态栏最近同步时间已改为仅显示 `YYYY-MM-DD`。

验证记录：

- `venv\Scripts\python.exe -m pytest tests\runtime\test_runtime_time_helpers.py tests\runtime\test_no_deprecated_utcnow.py -q`：3 passed
- `venv\Scripts\python.exe -W error::DeprecationWarning -m pytest tests\contracts\test_runtime_page_modules_contract.py -q`：7 passed
- `venv\Scripts\python.exe -m pytest tests\runtime -q`：71 passed
- `venv\Scripts\python.exe -m pytest tests\contracts -q`：26 passed
- `npm --prefix apps\desktop run test`：13 files / 29 tests passed
- `npm --prefix apps\desktop run build`：passed，Material Symbols 字体运行时解析提示为非阻断
- `git diff --check`：passed

## Scope

补充展示约束：状态栏和界面时间只显示年月日，格式固定为 `YYYY-MM-DD`；不显示时分秒、毫秒、`Z`、UTC offset 或 `Asia/Shanghai` 字样。时区仍按上海时区换算，存储与接口仍保留 UTC 标准时间。

本批主要处理 Runtime 时间生成方式；前端仅允许修改状态栏日期展示格式，不改业务语义、不新增 API、不改其他 UI 范围。

## File Map

- Create: `apps/py-runtime/src/common/time.py`
  - 统一提供 Runtime UTC 时间工具。
- Modify: `apps/py-runtime/src/repositories/account_repository.py`
  - 替换 `_utc_now()` 内部实现。
- Modify: `apps/py-runtime/src/repositories/asset_repository.py`
  - 替换 `_utc_now()` 内部实现。
- Modify: `apps/py-runtime/src/repositories/automation_repository.py`
  - 替换 DateTime 字段的 `datetime.utcnow()`。
- Modify: `apps/py-runtime/src/repositories/device_workspace_repository.py`
  - 替换 workspace 更新时间和 health check 时间。
- Modify: `apps/py-runtime/src/repositories/publishing_repository.py`
  - 替换发布计划更新时间、提交时间。
- Modify: `apps/py-runtime/src/repositories/render_repository.py`
  - 替换渲染任务更新时间、完成时间。
- Modify: `apps/py-runtime/src/repositories/review_repository.py`
  - 替换复盘摘要创建、更新、分析时间。
- Modify: `apps/py-runtime/src/services/account_service.py`
  - 替换 `_utc_now()` 内部实现。
- Modify: `apps/py-runtime/src/services/asset_service.py`
  - 替换 `_utc_now()` 内部实现。
- Modify: `apps/py-runtime/src/services/publishing_service.py`
  - 替换发布预检、提交结果 fallback 时间。
- Modify: `apps/py-runtime/src/services/review_service.py`
  - 替换分析结果 fallback 时间。
- Create: `tests/runtime/test_runtime_time_helpers.py`
  - 验证时间工具输出 UTC aware datetime 和 `Z` 后缀 ISO 字符串。
- Create: `tests/runtime/test_no_deprecated_utcnow.py`
  - 扫描 Runtime 源码，禁止重新引入 `datetime.utcnow()`。
- Modify: `apps/desktop/src/layouts/AppShell.vue`
  - 将状态栏最近同步时间格式化为 `YYYY-MM-DD`，不再追加时分秒或 `Asia/Shanghai`。
- Modify: `apps/desktop/tests/ai-system-settings.spec.ts`
  - 更新断言，确保最近同步时间只显示年月日。

## Task 1: Add UTC Time Helper And Guard Test

**Files:**
- Create: `apps/py-runtime/src/common/time.py`
- Create: `tests/runtime/test_runtime_time_helpers.py`
- Create: `tests/runtime/test_no_deprecated_utcnow.py`

- [ ] **Step 1: Write failing tests**

Create `tests/runtime/test_runtime_time_helpers.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime

from common.time import utc_now, utc_now_iso


def test_utc_now_returns_timezone_aware_utc_datetime() -> None:
    now = utc_now()

    assert isinstance(now, datetime)
    assert now.tzinfo is UTC


def test_utc_now_iso_uses_z_suffix() -> None:
    value = utc_now_iso()

    assert value.endswith("Z")
    assert "+00:00" not in value
    assert datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
```

Create `tests/runtime/test_no_deprecated_utcnow.py`:

```python
from __future__ import annotations

from pathlib import Path


def test_runtime_source_does_not_use_deprecated_utcnow() -> None:
    runtime_src = Path(__file__).resolve().parents[2] / "apps" / "py-runtime" / "src"
    offenders: list[str] = []

    for file_path in runtime_src.rglob("*.py"):
        if "__pycache__" in file_path.parts:
            continue
        text = file_path.read_text(encoding="utf-8")
        if "datetime.utcnow(" in text:
            offenders.append(str(file_path.relative_to(runtime_src)))

    assert offenders == []
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
venv\Scripts\python.exe -m pytest tests\runtime\test_runtime_time_helpers.py tests\runtime\test_no_deprecated_utcnow.py -q
```

Expected:

- `test_runtime_time_helpers.py` fails because `common.time` does not exist.
- `test_no_deprecated_utcnow.py` fails with current offender files.

- [ ] **Step 3: Add shared helper**

Create `apps/py-runtime/src/common/time.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")
```

- [ ] **Step 4: Run helper test again**

Run:

```powershell
venv\Scripts\python.exe -m pytest tests\runtime\test_runtime_time_helpers.py -q
```

Expected: helper tests pass.

## Task 2: Replace Runtime datetime.utcnow Calls

**Files:**
- Modify: `apps/py-runtime/src/repositories/account_repository.py`
- Modify: `apps/py-runtime/src/repositories/asset_repository.py`
- Modify: `apps/py-runtime/src/repositories/automation_repository.py`
- Modify: `apps/py-runtime/src/repositories/device_workspace_repository.py`
- Modify: `apps/py-runtime/src/repositories/publishing_repository.py`
- Modify: `apps/py-runtime/src/repositories/render_repository.py`
- Modify: `apps/py-runtime/src/repositories/review_repository.py`
- Modify: `apps/py-runtime/src/services/account_service.py`
- Modify: `apps/py-runtime/src/services/asset_service.py`
- Modify: `apps/py-runtime/src/services/publishing_service.py`
- Modify: `apps/py-runtime/src/services/review_service.py`

- [ ] **Step 1: Update string timestamp helpers**

For files that currently define:

```python
def _utc_now() -> str:
    return datetime.utcnow().isoformat()
```

Change imports and helper body to:

```python
from common.time import utc_now_iso


def _utc_now() -> str:
    return utc_now_iso()
```

Apply to:

- `apps/py-runtime/src/repositories/account_repository.py`
- `apps/py-runtime/src/repositories/asset_repository.py`
- `apps/py-runtime/src/services/account_service.py`
- `apps/py-runtime/src/services/asset_service.py`

- [ ] **Step 2: Update DateTime field assignments**

For files assigning `datetime.utcnow()` into SQLAlchemy `DateTime` model fields, import `utc_now`:

```python
from common.time import utc_now
```

Then replace examples like:

```python
checked_at = datetime.utcnow()
workspace.updated_at = datetime.utcnow()
```

with:

```python
checked_at = utc_now()
workspace.updated_at = utc_now()
```

Apply to:

- `apps/py-runtime/src/repositories/automation_repository.py`
- `apps/py-runtime/src/repositories/device_workspace_repository.py`
- `apps/py-runtime/src/repositories/publishing_repository.py`
- `apps/py-runtime/src/repositories/render_repository.py`
- `apps/py-runtime/src/repositories/review_repository.py`
- `apps/py-runtime/src/services/publishing_service.py`
- `apps/py-runtime/src/services/review_service.py`

- [ ] **Step 3: Remove unused datetime imports**

After replacement, remove now-unused direct `datetime` imports from files where only `utc_now` or `utc_now_iso` remains.

- [ ] **Step 4: Run guard test**

Run:

```powershell
venv\Scripts\python.exe -m pytest tests\runtime\test_no_deprecated_utcnow.py -q
```

Expected: pass.

## Task 3: Normalize Desktop Time Display

**Files:**
- Modify: `apps/desktop/src/layouts/AppShell.vue`
- Modify: `apps/desktop/tests/ai-system-settings.spec.ts`

- [ ] **Step 1: Write failing display assertion**

In `apps/desktop/tests/ai-system-settings.spec.ts`, change the status bar assertion from:

```typescript
expect(wrapper.text()).toContain("最近同步 2026-04-11 16:05:00 Asia/Shanghai");
```

to:

```typescript
expect(wrapper.text()).toContain("最近同步 2026-04-11");
expect(wrapper.text()).not.toContain("16:05:00");
expect(wrapper.text()).not.toContain("Asia/Shanghai");
expect(wrapper.text()).not.toContain("Z");
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
npm --prefix apps\desktop run test -- ai-system-settings.spec.ts
```

Expected: fails because the current label still includes time and appends `Asia/Shanghai`.

- [ ] **Step 3: Update display formatter**

In `apps/desktop/src/layouts/AppShell.vue`, keep `timeZone: "Asia/Shanghai"` in `Intl.DateTimeFormat`, but change the return value from:

```typescript
return `${part("year")}-${part("month")}-${part("day")} ${part("hour")}:${part("minute")}:${part("second")} Asia/Shanghai`;
```

to:

```typescript
return `${part("year")}-${part("month")}-${part("day")}`;
```

- [ ] **Step 4: Run display test again**

Run:

```powershell
npm --prefix apps\desktop run test -- ai-system-settings.spec.ts
```

Expected: pass.

## Task 4: Verify Contracts With Warnings As Errors

**Files:**
- Test only.

- [ ] **Step 1: Run targeted warning gate**

Run:

```powershell
venv\Scripts\python.exe -W error::DeprecationWarning -m pytest tests\contracts\test_runtime_page_modules_contract.py -q
```

Expected: pass without `datetime.utcnow()` deprecation failures.

- [ ] **Step 2: Run runtime regression**

Run:

```powershell
venv\Scripts\python.exe -m pytest tests\runtime -q
```

Expected: pass.

- [ ] **Step 3: Run contracts regression**

Run:

```powershell
venv\Scripts\python.exe -m pytest tests\contracts -q
```

Expected: pass.

- [ ] **Step 4: Run diff hygiene**

Run:

```powershell
git diff --check
```

Expected: no whitespace errors.

## Boundaries

- Do not alter API response envelope.
- Do not change route paths, DTO field names, or frontend contracts.
- Do not change SQLite schema or Alembic migrations in this batch.
- Frontend change is limited to status-bar time display formatting.
- Do not touch untracked `.ccb/`, Stitch scripts, or `tests/error/` unless separately requested.

## Acceptance

- `datetime.utcnow()` no longer appears under `apps/py-runtime/src`.
- Warning-as-error contract test passes.
- UI status bar time displays as `YYYY-MM-DD` only.
- Runtime and contract tests pass.
- No new product scope and no fake data.
