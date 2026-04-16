# Runtime UTC 时间清理与日期展示设计

> 计划来源：`docs/superpowers/plans/2026-04-16-runtime-utc-time-cleanup.md`
> 状态：已完成并通过验收
> 适用范围：Runtime 时间工具、M09-M15 repository/service 时间生成、桌面状态栏最近同步日期展示

## 验收记录

- Runtime 已统一使用 `common.time.utc_now()` / `common.time.utc_now_iso()`。
- `apps/py-runtime/src` 下已无 `datetime.utcnow(`。
- 桌面状态栏最近同步时间只显示 `YYYY-MM-DD`。
- warning-as-error 合同测试、runtime、contracts、desktop test、desktop build 均已通过。

## 1. 目标

清理 Runtime 中 `datetime.utcnow()` 弃用警告，统一使用 timezone-aware UTC 时间，避免后续测试在 Python 3.13+ 下被弃用警告污染。

同时修正桌面状态栏最近同步展示：用户界面只显示日期 `YYYY-MM-DD`，不显示时分秒、毫秒、`Z`、UTC offset 或 `Asia/Shanghai` 字样。

## 2. 非目标

- 不修改 Runtime API 路径、字段名、JSON 信封或业务语义。
- 不修改 SQLite schema 或 Alembic 迁移。
- 不新增前端页面、组件视觉改版或业务交互。
- 不处理 `.ccb/`、Stitch 脚本、`tests/error/` 等本轮无关文件。
- 不把本轮扩展为 M07 配音中心开发。

## 3. 设计决策

### 3.1 Runtime 时间源

新增 `apps/py-runtime/src/common/time.py`，提供两个函数：

```python
from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")
```

使用规则：

- SQLAlchemy `DateTime` 字段使用 `utc_now()`。
- 字符串时间字段使用 `utc_now_iso()`。
- repository/service 不再直接调用 `datetime.utcnow()`。
- 现有 DTO 字段和 API 响应格式不因本轮变更而重命名。

### 3.2 桌面日期展示

`apps/desktop/src/layouts/AppShell.vue` 继续使用 `Intl.DateTimeFormat` 按 `Asia/Shanghai` 换算日期，但格式化结果只返回：

```text
YYYY-MM-DD
```

示例：

```text
最近同步 2026-04-11
```

界面不得显示：

- `16:05:00`
- 毫秒
- `Z`
- `+08:00`
- `Asia/Shanghai`

### 3.3 测试防回归

新增 `tests/runtime/test_no_deprecated_utcnow.py` 扫描 `apps/py-runtime/src`，禁止重新引入：

```python
datetime.utcnow(
```

新增 `tests/runtime/test_runtime_time_helpers.py` 验证：

- `utc_now()` 返回 timezone-aware UTC datetime。
- `utc_now_iso()` 返回 `Z` 后缀字符串。

更新 `apps/desktop/tests/ai-system-settings.spec.ts`，断言状态栏只出现日期，不出现时分秒或时区字样。

## 4. 文件级设计

### Runtime

- `apps/py-runtime/src/common/time.py`
  - 新增共享时间工具。
- `apps/py-runtime/src/repositories/account_repository.py`
  - `_utc_now()` 改用 `utc_now_iso()`。
- `apps/py-runtime/src/repositories/asset_repository.py`
  - `_utc_now()` 改用 `utc_now_iso()`。
- `apps/py-runtime/src/repositories/automation_repository.py`
  - `task.updated_at`、任务运行时间改用 `utc_now()`。
- `apps/py-runtime/src/repositories/device_workspace_repository.py`
  - `workspace.updated_at`、`checked_at` 改用 `utc_now()`。
- `apps/py-runtime/src/repositories/publishing_repository.py`
  - 发布计划更新时间、提交时间改用 `utc_now()`。
- `apps/py-runtime/src/repositories/render_repository.py`
  - 渲染任务更新时间、完成时间改用 `utc_now()`。
- `apps/py-runtime/src/repositories/review_repository.py`
  - 复盘摘要创建、更新、分析时间改用 `utc_now()`。
- `apps/py-runtime/src/services/account_service.py`
  - `_utc_now()` 改用 `utc_now_iso()`。
- `apps/py-runtime/src/services/asset_service.py`
  - `_utc_now()` 改用 `utc_now_iso()`。
- `apps/py-runtime/src/services/publishing_service.py`
  - 预检时间、提交结果 fallback 时间改用 `utc_now()`。
- `apps/py-runtime/src/services/review_service.py`
  - 分析结果 fallback 时间改用 `utc_now()`。

### Frontend

- `apps/desktop/src/layouts/AppShell.vue`
  - `formatShanghaiDateTime()` 改为只返回日期。
- `apps/desktop/tests/ai-system-settings.spec.ts`
  - 更新最近同步断言。

## 5. 风险与控制

- 风险：SQLite 存储 timezone-aware datetime 时序列化表现受 SQLAlchemy 方言影响。
  - 控制：本轮不改 schema，只替换时间来源；runtime/contracts 回归覆盖现有读写链路。
- 风险：日期展示只显示日，可能隐藏具体同步时刻。
  - 控制：这是用户明确约束；状态栏只展示日期，内部 `lastSyncedAt` 仍保留完整时间。
- 风险：机械替换遗漏。
  - 控制：新增源码扫描测试，禁止 `datetime.utcnow(` 回流。

## 6. 验证矩阵

必须运行：

```powershell
venv\Scripts\python.exe -m pytest tests\runtime\test_runtime_time_helpers.py tests\runtime\test_no_deprecated_utcnow.py -q
npm --prefix apps\desktop run test -- ai-system-settings.spec.ts
venv\Scripts\python.exe -W error::DeprecationWarning -m pytest tests\contracts\test_runtime_page_modules_contract.py -q
venv\Scripts\python.exe -m pytest tests\runtime -q
venv\Scripts\python.exe -m pytest tests\contracts -q
git diff --check
```

如涉及提交前完整验收，再补跑：

```powershell
npm --prefix apps\desktop run test
npm --prefix apps\desktop run build
```

## 7. 通过标准

- `apps/py-runtime/src` 下不存在 `datetime.utcnow(`。
- warning-as-error 的合同测试通过。
- Runtime 与 contract 测试通过。
- 状态栏最近同步展示为 `YYYY-MM-DD`，不显示时分秒或时区字样。
- 没有 API 契约漂移、前端业务范围扩展或假数据新增。
