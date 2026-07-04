# 2026-05-25 Runtime 就绪链路设计规格

## 1. 对应计划

对应计划：`docs/superpowers/plans/2026-05-25-delivery-readiness.md`

本规格覆盖阶段 2 的第一批切片：首启、配置总线和 Runtime 就绪链路。

## 2. 目标

用户首次打开 TK-OPS 时，首启向导必须基于 Runtime 的真实 bootstrap 报告展示当前状态，而不是只凭配置字段推断：

- 目录初始化结果来自 `/api/bootstrap/initialize-directories`。
- Runtime 自检结果来自 `/api/bootstrap/runtime-selfcheck`。
- 首启 readiness 阻断项来自 `/api/bootstrap/readiness`。
- 首启页能展示真实阻断原因、影响对象、下一步动作和请求号。
- 配置总线统一持有 Runtime 健康、配置、诊断和 bootstrap readiness 状态，页面不各自发散请求。

本阶段不实现持久化任务总线、不实现真实渲染、不实现发布执行器。

## 3. 数据契约

前端新增 / 使用以下类型：

- `BootstrapReadinessAction`
- `BootstrapReadinessItem`
- `BootstrapReadinessBlocker`
- `BootstrapReadinessReport`

字段与 Runtime 契约一致：

```ts
type BootstrapReadinessReport = {
  status: string;
  canContinue: boolean;
  checkedAt: string;
  items: BootstrapReadinessItem[];
  blockers: BootstrapReadinessBlocker[];
};
```

新增 Runtime client：

```ts
export async function fetchBootstrapReadiness(): Promise<BootstrapReadinessReport>
```

该函数调用 `GET /api/bootstrap/readiness`，仍通过统一 `requestRuntime` 信封处理。

## 4. 配置总线规格

`useConfigBusStore` 增加以下状态：

- `bootstrapReadiness: BootstrapReadinessReport | null`
- `bootstrapDirectoryReport: BootstrapDirectoryReport | null`
- `runtimeSelfCheckReport: RuntimeSelfCheckReport | null`

`hydrate()` 和 `save()` 成功后应同步：

1. `fetchRuntimeHealth()`
2. `fetchRuntimeConfig()`
3. `fetchRuntimeDiagnostics()`
4. `fetchBootstrapReadiness()`

`initializeBootstrap()` 新动作：

1. 调用 `initializeDirectories()`
2. 调用 `runtimeSelfCheck()`
3. 调用 `fetchBootstrapReadiness()`
4. 更新三份 bootstrap 状态
5. 出错时走 `applyRuntimeError`

约束：

- 不在首启页面直接 fetch Runtime。
- 不吞异常；失败统一落到 `configBusStore.error`。
- silent provider readiness 可以继续保留，但错误日志必须使用中文。

## 5. 首启页规格

`SetupLicenseWizardPage.vue` 使用 `configBusStore.bootstrapReadiness` 驱动目录与 Runtime 自检展示：

- Runtime 步骤展示 self-check 分项：端口、数据库、依赖、目录状态。
- 初始化步骤展示 readiness items：许可证、目录初始化、Runtime 诊断、媒体依赖。
- 若 readiness 有 blockers，显示阻断原因、影响对象、下一步动作。
- “重新检测配置”应调用 `configBusStore.initializeBootstrap()`，而不是只读取 config。
- “继续初始化”仍跳转设置页，但按钮旁应说明当前阻断项来自 Runtime readiness。

文案要求：

- 全中文。
- 不展示 traceback。
- 不把 warning 当作完全 ready；warning 可继续但需要显示注意事项。

## 6. 测试规格

前端测试：

- `apps/desktop/tests/runtime-client-settings.spec.ts`
  - 验证 `fetchBootstrapReadiness()` 使用 `GET /api/bootstrap/readiness`。
- `apps/desktop/tests/core-runtime-store.spec.ts` 或新增 config bus 测试
  - 验证 `configBusStore.load()` 成功后持有 bootstrap readiness。
  - 验证 `initializeBootstrap()` 调用目录初始化、自检和 readiness。
- `apps/desktop/tests/setup-license-wizard.spec.ts`
  - 验证首启页展示 readiness 阻断项和下一步动作。
  - 验证重新检测初始化时调用 bootstrap 初始化链路。

Runtime 测试：

- 现有 `tests/contracts/test_bootstrap_contract.py` 和 `tests/runtime/test_bootstrap_routes.py` 继续覆盖后端契约。
- 本切片不改后端契约时无需新增后端测试。

验证命令：

```powershell
npm --prefix apps/desktop test -- runtime-client-settings core-runtime-store setup-license-wizard
npm --prefix apps/desktop test
npm --prefix apps/desktop run build
python -m pytest tests/contracts/test_bootstrap_contract.py tests/runtime/test_bootstrap_routes.py
```

## 7. 子代理分工

- `.codex/agents/engineering-backend-architect.toml`：只读确认 Runtime bootstrap 契约是否足以支撑本阶段。
- `.codex/agents/engineering-frontend-developer.toml`：实现 runtime-client、config-bus、首启页展示与测试。
- `.codex/agents/testing-api-tester.toml`：验证前后端 bootstrap 契约和错误路径。
- `.codex/agents/engineering-code-reviewer.toml`：最终审核真实数据、中文文案、配置总线边界。

主代理负责拆分范围、审核方向和最终验证。

## 8. 非目标

- 不修改许可证算法。
- 不修改后端 bootstrap 契约字段。
- 不把 AI Provider 配置写入首启页本地状态。
- 不绕过配置总线直接在页面内请求 Runtime。
