# Main 分支收口与文档统一 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前仓库所有尚未并入 `main` 的分支改动与本地未提交改动安全收口到 `main`，并同步更新版本、变更记录、项目进度和接口/状态文档，使仓库进入单一最新口径。

**Architecture:** 本次收口按“先冻结现状、再合并分支、后统一文档与版本、最后全量验证”的顺序推进，避免带着脏工作树直接 merge。Git 层以 `main` 为唯一收口分支；文档层以 `docs/PRD.md`、`docs/UI-DESIGN-PRD.md`、`docs/ARCHITECTURE-BOOTSTRAP.md`、`docs/RUNTIME-API-CALLS.md`、`docs/PROJECT-STATUS.md`、`README.md`、`CHANGELOG.md` 为统一更新面；版本层以根 `package.json#version` 为唯一真源。

**Tech Stack:** Git + PowerShell；Node.js 版本同步脚本；Tauri 2 + Vue 3 + TypeScript + Vite；Python + FastAPI + pytest；仓库文档真源与 `docs/superpowers/` 流程文档。

---

## Status

- 状态：Implemented，已于 2026-04-17 执行完成并收口到 `main`。
- 创建时间：2026-04-17。
- 本计划只覆盖 `main` 收口、未提交改动提交、版本与文档统一、验证与提交。
- 本计划不覆盖新的业务功能扩展，不新增第 17 页，不改产品定位，不新增假数据。
- 执行结果：已先提交主干脏工作树为 `58ecc75 chore: sync project status and desktop dev launcher`，再以 merge commit `6133b99` 合并 `codex/m05-ai-editing-workspace-runtime-ui`，并完成版本真源、状态文档与 Runtime 接口文档同步。
- 验证结果：`npm run version:check`、`npm --prefix apps/desktop run test`、`npm --prefix apps/desktop run build`、`venv\Scripts\python.exe -m pytest tests\runtime tests\contracts -q` 与 `git diff --check` 已通过。

## Current Facts

- 当前分支：`main`，`HEAD` 与 `origin/main` 对齐，当前提交为 `4455ed3`。
- 当前未并入 `main` 的本地分支只有一个：`codex/m05-ai-editing-workspace-runtime-ui`。
- 当前工作树不干净，存在已修改文件：
  - `CHANGELOG.md`
  - `README.md`
  - `apps/desktop/src-tauri/Cargo.toml`
  - `apps/desktop/src-tauri/tauri.conf.json`
  - `package.json`
  - `scripts/run-desktop-app.mjs`
- 当前工作树存在未跟踪文件：
  - `docs/PROJECT-STATUS.md`
  - `scripts/stitch-connect.js`
  - `scripts/stitch-generate-dashboard.js`
- 已知文档口径差异：
  - 根 `README.md` 已把 TaskBus、视频导入、配音中心、资产中心、M09-M15 Runtime 页面接线写成阶段性基线。
  - `apps/desktop/README.md` 仍写成“除 Dashboard、许可证向导、AI 设置、脚本页、分镜页外，其余页面仍为空态占位”。
  - `docs/PROJECT-STATUS.md` 已记录路由导航分组与 UI 真源口径不一致。
  - `docs/RUNTIME-API-CALLS.md` 仍需核对 M10-M15 页面现状和调用登记是否与代码一致。

## Scope

### 本轮必须完成

- 确认并合并所有尚未进入 `main` 的本地分支改动。
- 审核并提交当前 `main` 上未提交与未跟踪文件。
- 统一版本真源与镜像版本文件。
- 统一 `README.md`、`apps/desktop/README.md`、`CHANGELOG.md`、`docs/PROJECT-STATUS.md`、`docs/RUNTIME-API-CALLS.md` 的当前状态口径。
- 运行版本、前端、后端、文档和 Git 提交前检查。
- 让 `main` 回到“已提交、可验证、文档口径一致”的状态。

### 本轮明确不做

- 不扩展新的产品范围、页面或模块。
- 不重写已合并历史提交。
- 不 force push。
- 不为了“看起来完整”编造进度、接口或页面落地状态。
- 不把 `.claude/plan/` 历史蓝图直接当作当前实现事实。

## 文件地图

Git / 收口：

- 使用：仓库根 `.git`
- 核对：`git branch -vv`
- 核对：`git branch --no-merged main`
- 核对：`git worktree list`

版本与启动脚本：

- Modify: `package.json`
- Modify: `apps/desktop/src-tauri/Cargo.toml`
- Modify: `apps/desktop/src-tauri/tauri.conf.json`
- Modify: `scripts/run-desktop-app.mjs`
- Verify: `scripts/version-sync.mjs`
- Verify: `scripts/version-check.mjs`

状态与真源文档：

- Modify: `README.md`
- Modify: `apps/desktop/README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/PROJECT-STATUS.md`
- Modify: `docs/RUNTIME-API-CALLS.md`
- Reference only: `docs/PRD.md`
- Reference only: `docs/UI-DESIGN-PRD.md`
- Reference only: `docs/ARCHITECTURE-BOOTSTRAP.md`

待审核新增脚本：

- Review and decide commit: `scripts/stitch-connect.js`
- Review and decide commit: `scripts/stitch-generate-dashboard.js`

验证：

- `tests/contracts/test_runtime_page_modules_contract.py`
- `tests/contracts/test_text_encoding_contract.py`
- `tests/contracts/`
- `tests/runtime/`
- `apps/desktop/tests/`

## 阶段目标

### 阶段 1：冻结现状并完成收口清单

目标：

- 确认未并分支数量。
- 确认当前脏工作树内容是否都属于本次收口。
- 确认版本真源与当前改动关系。

输出：

- 只剩一个明确待合并分支或确认没有待合并分支。
- 当前未提交文件被分类为：直接提交、需要改写、需要放弃。

边界：

- 不在此阶段直接 merge。
- 不在未理解内容前批量 add/commit。

回退点：

- 若发现未提交文件与目标无关或来源不明，则停止进入下一阶段，先补充说明。

### 阶段 2：先提交当前 `main` 上未提交改动

目标：

- 让当前工作树从“脏状态”进入“可 merge 状态”。

策略：

- 逐项审阅未提交文件。
- 对确认为本次收口的一组变更形成首个提交。

候选提交范围：

- `CHANGELOG.md`
- `README.md`
- `apps/desktop/src-tauri/Cargo.toml`
- `apps/desktop/src-tauri/tauri.conf.json`
- `package.json`
- `scripts/run-desktop-app.mjs`
- `docs/PROJECT-STATUS.md`
- `scripts/stitch-connect.js`
- `scripts/stitch-generate-dashboard.js`

要求：

- 提交说明必须体现“启动链路/项目状态文档同步/版本镜像同步”这类真实语义。
- 提交后 `git status --short` 必须为空，才能进入 merge 阶段。

回退点：

- 若 `git diff --check` 失败，先修格式问题再提交。

### 阶段 3：将未并分支合入 `main`

目标：

- 将 `codex/m05-ai-editing-workspace-runtime-ui` 合并到 `main`。

策略：

- 优先使用 `git merge --no-ff codex/m05-ai-editing-workspace-runtime-ui` 保留分支收口语义。
- 若有冲突，只按真源文档和现有实现边界解决，不回退产品定位。

合并后必须核查：

- `apps/desktop/src/app/router/`
- `apps/desktop/src/pages/workspace/`
- `apps/py-runtime/src/api/routes/`
- `tests/`
- `docs/`

回退点：

- 冲突范围若超出 M05 工作台与当前主干状态同步的合理范围，则 `git merge --abort`，先补 spec 再重做。

### 阶段 4：统一版本、文档、进度口径

目标：

- 让文档与代码对齐到“合并后的最新状态”。

必须更新的口径：

- 根 `README.md`：当前边界、模块状态引用、版本说明。
- `apps/desktop/README.md`：真实已落地/已接线页面现状，不能继续写过时的“其余页面均为空态占位”。
- `CHANGELOG.md`：记录本次收口、merge 和文档统一。
- `docs/PROJECT-STATUS.md`：更新版本号、页面状态、待收口问题、已并主干状态。
- `docs/RUNTIME-API-CALLS.md`：核对已存在 Runtime routes 与前端调用登记，至少补到当前代码真实覆盖范围。
- 若本次需要升级版本，则以根 `package.json#version` 为唯一真源，并运行版本同步脚本更新镜像文件。

边界：

- 文档只能记录真实已落地、已接线、待深化状态。
- 不得为了“统一”删除已知风险；风险应保留为待收口项。

回退点：

- 若文档更新后与真源冲突，优先修文档，不修改产品真源定义。

### 阶段 5：验证、最终提交与收尾

目标：

- 证明合并后的 `main` 是可构建、可测试、版本一致、文档一致的。

必跑验证：

- `npm run version:sync`
- `npm run version:check`
- `npm --prefix apps/desktop run test`
- `npm --prefix apps/desktop run build`
- `venv\Scripts\python.exe -m pytest tests\contracts -q`
- `venv\Scripts\python.exe -m pytest tests\runtime -q`
- `venv\Scripts\python.exe -m pytest tests\contracts\test_text_encoding_contract.py -q`
- `git diff --check`
- `git status --short --branch`

完成标准：

- `main` 工作树干净。
- 无未并入 `main` 的本地分支。
- 版本检查通过。
- 前后端相关测试通过。
- 文档口径一致，且不再出现同一状态在不同文档中相互矛盾。

## Implementation Tasks

### Task 1：盘点未并分支与当前脏工作树

**Files:**

- Read: `.git`
- Read: `README.md`
- Read: `apps/desktop/README.md`
- Read: `docs/PROJECT-STATUS.md`
- Read: `docs/RUNTIME-API-CALLS.md`

- [x] **Step 1: 列出所有分支与未并分支**

Run:

```powershell
git branch -vv
git branch --no-merged main
git worktree list
```

Expected:

- 明确只有哪些分支尚未进 `main`。
- worktree 中若存在 detached HEAD，只记录事实，不当作 branch 自动 merge。

- [x] **Step 2: 审查当前工作树**

Run:

```powershell
git status --short --branch
git diff --stat
git diff -- CHANGELOG.md README.md package.json apps/desktop/src-tauri/Cargo.toml apps/desktop/src-tauri/tauri.conf.json scripts/run-desktop-app.mjs
```

Expected:

- 明确每个改动属于启动链路、版本、文档状态或新增脚本。

- [x] **Step 3: 审查新增未跟踪文件内容**

Run:

```powershell
Get-Content -Raw -Encoding utf8 docs/PROJECT-STATUS.md
Get-Content -Raw -Encoding utf8 scripts/stitch-connect.js
Get-Content -Raw -Encoding utf8 scripts/stitch-generate-dashboard.js
```

Expected:

- 确认这些新增文件属于本次“统一到最新”的范围，而不是无关草稿。

### Task 2：提交当前 `main` 上的未提交改动

**Files:**

- Modify if needed: `README.md`
- Modify if needed: `apps/desktop/README.md`
- Modify if needed: `CHANGELOG.md`
- Modify if needed: `docs/PROJECT-STATUS.md`
- Modify if needed: `package.json`
- Modify if needed: `apps/desktop/src-tauri/Cargo.toml`
- Modify if needed: `apps/desktop/src-tauri/tauri.conf.json`
- Modify if needed: `scripts/run-desktop-app.mjs`
- Add if accepted: `scripts/stitch-connect.js`
- Add if accepted: `scripts/stitch-generate-dashboard.js`

- [x] **Step 1: 修正当前未提交改动中的明显口径冲突**

至少处理：

- 根 `README.md` 与 `docs/PROJECT-STATUS.md` 的当前阶段口径一致。
- `apps/desktop/README.md` 不再保留过时页面状态描述。
- `CHANGELOG.md` 与本次实际改动内容一致。

- [x] **Step 2: 运行提交前格式检查**

Run:

```powershell
git diff --check
```

Expected:

- 无空白和补丁格式错误。

- [x] **Step 3: 提交当前工作树改动**

Run:

```powershell
git add CHANGELOG.md README.md apps/desktop/README.md apps/desktop/src-tauri/Cargo.toml apps/desktop/src-tauri/tauri.conf.json package.json scripts/run-desktop-app.mjs docs/PROJECT-STATUS.md scripts/stitch-connect.js scripts/stitch-generate-dashboard.js
git commit -m "chore: sync project status and desktop dev launcher"
```

Expected:

- 形成一条干净、可审计的收口前提交。

### Task 3：合并未并分支到 `main`

**Files:**

- Merge target: branch `codex/m05-ai-editing-workspace-runtime-ui`

- [x] **Step 1: 执行分支合并**

Run:

```powershell
git merge --no-ff codex/m05-ai-editing-workspace-runtime-ui
```

Expected:

- 成功生成 merge commit，或进入可控冲突解决流程。

- [x] **Step 2: 本次 merge 无冲突，逐文件解决步骤未触发**

重点核对：

- `apps/desktop/src/app/router/`
- `apps/desktop/src/pages/workspace/`
- `apps/desktop/src/modules/`
- `apps/py-runtime/src/api/routes/`
- `tests/`
- `docs/`

Expected:

- 合并结果遵循当前真源文档与主干现状，不把旧蓝图或实验实现硬塞回运行链路。

- [x] **Step 3: 确认不存在新的未并分支**

Run:

```powershell
git branch --no-merged main
```

Expected:

- 无输出。

### Task 4：统一版本与文档

**Files:**

- Modify: `package.json`
- Modify: `apps/desktop/src-tauri/Cargo.toml`
- Modify: `apps/desktop/src-tauri/tauri.conf.json`
- Modify: `apps/py-runtime/pyproject.toml`
- Modify: `README.md`
- Modify: `apps/desktop/README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/PROJECT-STATUS.md`
- Modify: `docs/RUNTIME-API-CALLS.md`

- [x] **Step 1: 决定版本号**

规则：

- 若合并结果包含新的功能面或状态收口，升级到新 patch 版本。
- 版本只改根 `package.json#version`，再同步镜像文件。

- [x] **Step 2: 同步版本镜像**

Run:

```powershell
npm run version:sync
npm run version:check
```

Expected:

- `version:check` 成功，所有镜像版本一致。

- [x] **Step 3: 统一状态文档**

至少处理：

- `README.md` 当前边界与项目状态文档一致。
- `apps/desktop/README.md` 页面落地现状更新到合并后事实。
- `docs/PROJECT-STATUS.md` 更新当前版本、页面状态、已知待收口问题。
- `docs/RUNTIME-API-CALLS.md` 补齐当前已存在页面和调用登记，避免“代码已存在但唯一接口文档未记录”。
- `CHANGELOG.md` 追加本次 merge 与统一记录。

### Task 5：全量验证并完成最终提交

**Files:**

- Verify only: `apps/desktop/`
- Verify only: `apps/py-runtime/`
- Verify only: `tests/`
- Verify only: `docs/`

- [x] **Step 1: 跑版本与文档验证**

Run:

```powershell
npm run version:check
venv\Scripts\python.exe -m pytest tests\contracts\test_text_encoding_contract.py -q
```

Expected:

- 版本一致。
- 文档 UTF-8 与文本契约通过。

- [x] **Step 2: 跑前端验证**

Run:

```powershell
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
```

Expected:

- 全部通过；若有非阻断 warning，需在最终说明中标注。

- [x] **Step 3: 跑后端验证**

Run:

```powershell
venv\Scripts\python.exe -m pytest tests\contracts -q
venv\Scripts\python.exe -m pytest tests\runtime -q
```

Expected:

- contracts 与 runtime 测试通过。

- [x] **Step 4: 跑 Git 收尾检查**

Run:

```powershell
git diff --check
git status --short --branch
```

Expected:

- 无 diff 格式错误。
- `main` 工作树干净。

- [x] **Step 5: 提交最终收口改动**

Run:

```powershell
git add package.json apps/desktop/src-tauri/Cargo.toml apps/desktop/src-tauri/tauri.conf.json apps/py-runtime/pyproject.toml README.md apps/desktop/README.md CHANGELOG.md docs/PROJECT-STATUS.md docs/RUNTIME-API-CALLS.md
git commit -m "chore: consolidate main branch and sync docs"
```

Expected:

- `main` 上留下明确的收口提交。

## Verification Matrix

Git：

```powershell
git branch --no-merged main
git status --short --branch
git diff --check
```

版本：

```powershell
npm run version:sync
npm run version:check
```

前端：

```powershell
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
```

后端：

```powershell
venv\Scripts\python.exe -m pytest tests\contracts -q
venv\Scripts\python.exe -m pytest tests\runtime -q
```

文档：

```powershell
venv\Scripts\python.exe -m pytest tests\contracts\test_text_encoding_contract.py -q
```

## Risks And Guardrails

- 当前脏工作树必须先提交，否则 merge 容易失败或把状态混在一起。
- `codex/m05-ai-editing-workspace-runtime-ui` 合并后若带入旧文档口径，需要以当前主干真源为准回收。
- `docs/RUNTIME-API-CALLS.md` 必须保持唯一接口文档地位，不得再另写并行接口说明。
- 版本升级后必须跑 `version:check`，不能只改根 `package.json`。
- 文档只记录真实状态；未完成能力必须明确写“待深化/待接线/待计划”，不能写成“已落地”。

## Approval Gate

- 本计划已获批。
- 下一步按仓库流程生成对应 design spec：`docs/superpowers/specs/2026-04-17-main-branch-consolidation-design.md`
- design spec 经用户确认后，再进入实际合并、提交、版本同步和验证
