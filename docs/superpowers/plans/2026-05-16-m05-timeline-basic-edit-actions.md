# M05 时间线基础编辑动作 Implementation Plan

## Goal

在既有 M05 基础剪辑工作台 UI 和 Runtime 时间线能力上，补齐第一批真实编辑动作：选中、删除片段、按当前播放头分割片段。保持范围小，不引入拖拽排序、复杂吸附、撤销栈或真实媒体播放。

## Scope

实现内容：

- Runtime 新增 `DELETE /api/workspace/clips/{clip_id}`。
- Runtime 新增 `POST /api/workspace/clips/{clip_id}/split`，按毫秒位置把一个片段拆成两个相邻片段。
- 前端 Runtime Client 增加 `deleteWorkspaceClip`、`splitWorkspaceClip`。
- `editing-workspace` store 增加 `deleteSelectedClip()`、`splitSelectedClip()`，复用统一错误处理和 `WorkspaceTimelineResultDto`。
- M05 工具条的“分割 / 删除”从禁用视觉态改为可触发按钮；没有选中片段或不可分割时保持禁用并提供中文状态。
- 补齐 Runtime、契约、store、页面测试和接口文档。

不做内容：

- 不做拖拽移动。
- 不做边缘拖拽裁剪。
- 不做撤销 / 重做。
- 不做跨轨道移动。
- 不做真实媒体重新渲染。
- 不在 UI 层直接拼接或保存轨道业务规则。

## File Map

Runtime:

- `apps/py-runtime/src/schemas/workspace.py`
- `apps/py-runtime/src/services/workspace_service.py`
- `apps/py-runtime/src/api/routes/workspace.py`
- `tests/runtime/test_workspace_service.py`
- `tests/contracts/test_workspace_runtime_contract.py`

Desktop:

- `apps/desktop/src/types/runtime.ts`
- `apps/desktop/src/app/runtime-client.ts`
- `apps/desktop/src/stores/editing-workspace.ts`
- `apps/desktop/src/modules/workspace/WorkspaceTimelineToolbar.vue`
- `apps/desktop/src/pages/workspace/AIEditingWorkspacePage.vue`
- `apps/desktop/tests/runtime-client-b-s4.spec.ts`
- `apps/desktop/tests/editing-workspace-store.spec.ts`
- `apps/desktop/tests/ai-editing-workspace-page.spec.ts`
- `apps/desktop/tests/workspace-layout-contract.spec.ts`

Docs:

- `docs/RUNTIME-API-CALLS.md`
- `CHANGELOG.md`

## Tasks

1. 先写失败测试：Runtime 删除、Runtime 分割、契约路由、前端 store、页面工具按钮。
2. 实现后端 schema、service、route。
3. 实现前端 client、store、工具条事件和页面处理。
4. 更新 Runtime API 文档与 changelog。
5. 运行聚焦测试，再运行桌面端回归测试。

## Verification

- `pytest tests/runtime/test_workspace_service.py tests/contracts/test_workspace_runtime_contract.py -q`
- `npm --prefix apps/desktop run test -- runtime-client-b-s4.spec.ts editing-workspace-store.spec.ts ai-editing-workspace-page.spec.ts workspace-layout-contract.spec.ts`
- `npm --prefix apps/desktop run test`

