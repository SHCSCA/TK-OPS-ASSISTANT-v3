# Main 分支收口与文档统一设计 Spec

> 日期：2026-04-17
> 来源计划：`docs/superpowers/plans/2026-04-17-main-branch-consolidation.md`
> 状态：Implemented，已于 2026-04-17 获批执行并完成 `main` 收口
> 适用流程：`tkops-agent-council` + `tkops-runtime-contract-council`
> 实施结论：已按“先提交主干脏工作树 -> 再 merge -> 再同步版本/文档 -> 最后验证”的顺序完成收口，merge 过程无冲突。
> 验证结论：版本检查、前端测试/构建、Runtime/契约测试与 Git diff 检查已通过。

## 1. 设计目标

这次工作不是新增产品功能，而是把 TK-OPS 当前本地仓库收口到一个可持续推进的主干状态。目标是让 `main` 成为唯一最新分支，让尚未并入 `main` 的本地工作进入主干，让当前未提交改动进入可审计提交，并让版本、变更记录、项目状态和 Runtime 接口文档统一到真实最新口径。

验收时需要满足四个结果：

1. `main` 成为唯一收口分支，本地不再存在未并入 `main` 的业务分支。
2. 当前未提交与未跟踪文件都被明确处理并进入提交，而不是继续停留在脏工作树。
3. 版本真源、镜像版本和桌面启动链路保持一致。
4. `README.md`、`apps/desktop/README.md`、`CHANGELOG.md`、`docs/PROJECT-STATUS.md`、`docs/RUNTIME-API-CALLS.md` 对当前实现状态的描述不再互相冲突。

## 2. 非目标

- 不新增任何产品页面、模块或业务能力。
- 不修改 `docs/PRD.md`、`docs/UI-DESIGN-PRD.md`、`docs/ARCHITECTURE-BOOTSTRAP.md` 的产品与架构真源定义。
- 不编造“已完成”状态来掩盖仍待深化的页面或 Runtime 能力。
- 不 force push，不重写历史，不清理用户未明确要求删除的分支和 worktree。
- 不把历史 `.claude/plan/` 蓝图误记成当前已实现事实。

## 3. Council 结论

本轮未 spawn 真实 subagent；Project Leader 在当前线程模拟必要角色。

### 3.1 Council roles

- Product Manager
- Frontend Lead
- Backend Runtime Lead
- Data & Contract Agent
- QA & Verification Agent
- Independent Reviewer

### 3.2 Facts found

- 当前 `main` 与 `origin/main` 对齐，当前提交为 `4455ed3`。
- 本地唯一未并入 `main` 的分支为 `codex/m05-ai-editing-workspace-runtime-ui`。
- 当前工作树不干净，已修改文件涉及版本、桌面启动脚本、根文档，未跟踪文件涉及项目状态文档与 Stitch 相关脚本。
- 根 `README.md` 与 `docs/PROJECT-STATUS.md` 已把若干模块写成阶段性基线，而 `apps/desktop/README.md` 仍保留更早期的页面状态描述。
- `docs/PROJECT-STATUS.md` 已明确记录 `route-manifest.ts` 当前导航分组口径与 UI 真源不一致，这个问题必须保留为已知风险，不能在收口文档里被抹掉。
- `docs/RUNTIME-API-CALLS.md` 是唯一接口真源，但仍需根据合并后的实际代码补齐当前覆盖范围。

### 3.3 Role consensus

| 角色 | 结论 | 关键判断 | 风险 | 验收建议 |
| --- | --- | --- | --- | --- |
| Product Manager | 通过 | 这次工作是主干收口，不改变 16 页范围和产品定位 | 文档可能把“已接线”写成“已落地” | 页面状态必须继续区分“已落地 / 已接线 / 待深化” |
| Frontend Lead | 通过 | `apps/desktop/README.md` 和桌面启动脚本是本次必须统一的前端入口口径 | 启动方式和页面现状口径可能继续分裂 | 以代码、测试和状态文档为准统一桌面端说明 |
| Backend Runtime Lead | 条件通过 | `docs/RUNTIME-API-CALLS.md` 只能记录真实 Runtime 与前端调用，不得复制历史计划语句 | 若 merge 后未补接口登记，会继续造成真源失真 | 合并后按 route、runtime-client、store 三点交叉核对接口文档 |
| Data & Contract Agent | 通过 | 版本唯一真源必须仍是根 `package.json#version` | 只改根版本不跑镜像同步会造成版本漂移 | 必须运行 `npm run version:sync` 与 `npm run version:check` |
| QA & Verification Agent | 通过 | 必须把 merge、版本、前端、后端、文档编码与 Git 检查都跑完 | 只看 `git status` 不足以证明已完成 | 以前端 test/build、后端 tests、版本检查和 `git diff --check` 为准 |
| Independent Reviewer | 8.4 / 10 | 路径清楚，核心是先提交脏工作树再 merge | P2：若直接在脏树上 merge，后续冲突和审计成本会升高 | 严格按“先提交当前改动，再 merge，再统一文档”的顺序执行 |

### 3.4 Leader decision

通过。设计成立，执行顺序固定为：

1. 先审查并提交当前 `main` 上的未提交改动。
2. 再将 `codex/m05-ai-editing-workspace-runtime-ui` 合并进 `main`。
3. 再统一版本、项目状态、接口文档和变更记录。
4. 最后运行全量验证并提交最终收口改动。

## 4. Git 收口设计

### 4.1 收口原则

- `main` 是唯一主干。
- 任何尚未并入 `main` 的业务分支都必须明确处理，不能长期与 `main` 并行漂移。
- 当前脏工作树必须先进入可审计提交，再进行 merge，避免把“主干已有但未提交的改动”和“待合并分支改动”混在一个 merge 里。
- Detached worktree 只作为状态事实记录，不自动视作独立分支收口对象。

### 4.2 本次 Git 路径

本次收口路径固定为：

1. 审查并提交当前 `main` 脏工作树。
2. 执行 `git merge --no-ff codex/m05-ai-editing-workspace-runtime-ui`。
3. 若 merge 产生冲突，只按当前真源文档、当前主干代码与真实测试结果解决。
4. merge 后再次检查 `git branch --no-merged main`，直到无输出。

### 4.3 冲突处理边界

优先核对的冲突区域：

- `apps/desktop/src/app/router/`
- `apps/desktop/src/pages/workspace/`
- `apps/desktop/src/modules/`
- `apps/py-runtime/src/api/routes/`
- `tests/`
- `docs/`

冲突处理规则：

- 不允许把旧产品口径、旧壳路径或历史蓝图重新带回运行链路。
- 不允许为了快速合并而删除主干已经存在的真源文档更新。
- 若 M05 分支中的实现与当前主干已存在实现部分重叠，则以更接近真源、更容易验证、更少假状态的一侧为准。

## 5. 版本与启动链路设计

### 5.1 版本规则

- 唯一可编辑版本真源仍是根 `package.json#version`。
- 镜像版本必须同步到：
  - `apps/desktop/src-tauri/Cargo.toml`
  - `apps/desktop/src-tauri/tauri.conf.json`
  - `apps/py-runtime/pyproject.toml`
- 版本是否提升由合并结果决定；如果合并后主干语义已发生“新批次已收口”的变化，则应提升 patch 版本。

### 5.2 启动链路规则

`scripts/run-desktop-app.mjs`、`package.json`、`apps/desktop/src-tauri/tauri.conf.json` 的启动口径必须一致：

- `app:dev` 以根脚本驱动。
- Tauri dev 启动参数不能再分裂成多个不一致写法。
- 若脚本支持复用已有 Runtime 或前端 dev server，README 和桌面 README 的开发说明必须同步体现。

### 5.3 版本与启动验证

必须通过以下命令证明一致：

```powershell
npm run version:sync
npm run version:check
```

以及：

```powershell
npm --prefix apps/desktop run build
```

## 6. 文档统一设计

### 6.1 文档分层

本次需要统一的不是“所有文档内容相同”，而是“每份文档只讲自己负责的真相，且彼此不冲突”。

- `README.md`：仓库级当前阶段、版本真源、开发入口和当前边界。
- `apps/desktop/README.md`：桌面端目录职责、当前已落地/已接线页面现状、开发态启动说明。
- `CHANGELOG.md`：本次收口和合并的变更记录。
- `docs/PROJECT-STATUS.md`：16 页状态表、当前阶段、已知待收口问题。
- `docs/RUNTIME-API-CALLS.md`：唯一 Runtime 接口与前端调用文档。

### 6.2 文档统一规则

- 页面状态只允许使用真实分级，如“已落地 / 已接线 / 部分接线 / 待深化”。
- 未完成的 Provider、字幕对齐、时间线、渲染、发布执行层必须继续显式标记为待后续计划，不得被改写为“已完成”。
- 已知风险必须保留，例如导航分组与 UI 真源口径差异，不能因为本次收口而从状态文档里删除。
- `docs/RUNTIME-API-CALLS.md` 只能依据实际 route、runtime-client、store 和测试来更新，不得抄写未落地的设计文案。

### 6.3 Stitch 脚本的定位

`scripts/stitch-connect.js` 与 `scripts/stitch-generate-dashboard.js` 若保留进仓库，必须在文档和提交语义上明确它们是辅助脚本，而不是新的运行主链入口。它们不能改变以下事实：

- 新功能仍只落在 `apps/desktop`、`apps/py-runtime`、`tests`、`docs` 边界内。
- Stitch 产物只作为参考或辅助，不替代 Vue/Tauri 正式实现。

## 7. Runtime 契约收口设计

本次虽然不是新增 Runtime 功能，但会修改 Runtime 唯一接口文档，因此仍需按 Runtime contract-first 规则执行。

### 7.1 API boundary

- 本次不新增或删除 Runtime route。
- 只允许更新 `docs/RUNTIME-API-CALLS.md`，使其与已存在 route、`runtime-client.ts`、Pinia store 和前端测试一致。
- 若在 merge 中带入新的 Runtime 页面接线或 M05 相关接口说明，必须用代码事实重新核对，而不是直接采纳分支文档口径。

### 7.2 Data contract

更新接口文档时，每条登记至少能回答：

- 后端入口在哪个 `api/routes/*.py`
- 前端调用函数是哪一个 `runtime-client.ts` 方法
- 由哪个 store 或页面消费
- 哪个 contract / runtime / frontend test 覆盖

### 7.3 Error/logging behavior

- 文档中所有错误说明继续遵守统一 JSON 信封：`{ "ok": false, "error": "中文可见错误" }`
- 不能在接口文档里把开发期 traceback、假进度或假任务状态写成正式契约。

## 8. Ownership map

Project Leader 在主线程串行执行，不启用真实 worker。文件责任按以下边界处理：

- Git 与 merge：主线程统一负责
- 版本与启动脚本：
  - `package.json`
  - `apps/desktop/src-tauri/Cargo.toml`
  - `apps/desktop/src-tauri/tauri.conf.json`
  - `apps/py-runtime/pyproject.toml`
  - `scripts/run-desktop-app.mjs`
- 仓库与桌面端说明：
  - `README.md`
  - `apps/desktop/README.md`
- 状态与接口真源：
  - `CHANGELOG.md`
  - `docs/PROJECT-STATUS.md`
  - `docs/RUNTIME-API-CALLS.md`
- 辅助脚本审查：
  - `scripts/stitch-connect.js`
  - `scripts/stitch-generate-dashboard.js`

## 9. 验证设计

### 9.1 Git 验证

```powershell
git branch --no-merged main
git status --short --branch
git diff --check
```

通过条件：

- 无未并分支。
- `main` 工作树干净。
- 无 diff 格式错误。

### 9.2 版本验证

```powershell
npm run version:sync
npm run version:check
```

通过条件：

- 根版本与镜像版本一致。

### 9.3 前端验证

```powershell
npm --prefix apps/desktop run test
npm --prefix apps/desktop run build
```

通过条件：

- 测试通过。
- 构建通过。
- 如有非阻断 warning，需在最终说明中列出。

### 9.4 后端验证

```powershell
venv\Scripts\python.exe -m pytest tests\contracts -q
venv\Scripts\python.exe -m pytest tests\runtime -q
```

通过条件：

- contract 与 runtime 测试通过。

### 9.5 文档编码验证

```powershell
venv\Scripts\python.exe -m pytest tests\contracts\test_text_encoding_contract.py -q
```

通过条件：

- 文档 UTF-8 与文本契约通过。

## 10. 风险与回退

### 10.1 主要风险

- 在脏工作树上直接 merge，会把两类变化混成一个不可审计结果。
- M05 分支合并可能带入过时文档口径或与主干已存在实现重叠的代码。
- 文档统一时最容易把“阶段性基线”误写成“全面落地”。
- 版本同步若漏掉镜像文件，会造成后续构建与文档不一致。

### 10.2 回退策略

- 若当前未提交改动审查后发现来源不明或超出收口范围，先停在提交前阶段，不进入 merge。
- 若 `git merge --no-ff codex/m05-ai-editing-workspace-runtime-ui` 冲突失控，则执行 `git merge --abort`，回到当前提交点重新评估。
- 若文档统一后与真源冲突，以修正文档为主，不反向改真源定义。
- 若验证失败，不进入最终收口提交，先根据失败类型回到对应阶段修复。

## 11. 验收标准

本 design spec 可以通过，前提是执行结果满足：

- `main` 成为唯一最新业务主干。
- 当前未提交和未跟踪文件被明确处理并进入提交。
- `package.json`、Tauri 镜像版本与 Python 镜像版本一致。
- `README.md`、`apps/desktop/README.md`、`CHANGELOG.md`、`docs/PROJECT-STATUS.md`、`docs/RUNTIME-API-CALLS.md` 口径一致且只记录真实状态。
- 前端测试、构建，后端 contract/runtime tests，文档编码测试和 Git 收尾检查全部通过。
- 无 unresolved P0/P1。
- Independent Reviewer 评分保持 >= 7.0。
