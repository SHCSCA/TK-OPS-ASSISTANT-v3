# M05 到 M14 导出交接 Implementation Plan

## 目标

让用户从 M05 AI 剪辑工作台点击“送往渲染与导出中心”后，在 M14 顶部看到清晰的交接上下文：来源是 AI 剪辑工作台、当前项目是否匹配、时间线 ID 是否存在、下一步是否可以创建渲染任务。

上一轮只做导出前的上下文识别与可见阻断，不自动创建 `RenderTask`。本轮补齐最小 `timeline_id` 契约：用户在有效交接状态下手动创建渲染任务时，Runtime 必须保存并返回来源时间线 ID。

本轮仍不扩展 FFmpeg 或完整时间线合成。

## 范围

可改文件：

- `apps/desktop/src/pages/renders/RenderExportCenterPage.vue`
- `apps/desktop/src/pages/renders/RenderExportCenterPage.css`
- `apps/desktop/src/modules/renders/renderWorkspaceHandoff.ts`
- `apps/desktop/src/modules/renders/RenderWorkspaceHandoffCard.vue`
- `apps/desktop/tests/render-export-center.spec.ts`
- `apps/desktop/src/types/runtime.ts`
- `apps/py-runtime/src/domain/models/render.py`
- `apps/py-runtime/src/schemas/renders.py`
- `apps/py-runtime/src/services/render_service.py`
- `apps/py-runtime/alembic/versions/`
- `tests/runtime/test_render_service.py`
- `tests/contracts/test_renders_runtime_contract.py`

不改范围：

- FFmpeg 与完整时间线合成逻辑
- M05 预览、时间线同步、导出就绪卡逻辑
- 路由树与 16 页范围
- 旧壳 `desktop_app/`

## 实施步骤

1. 新增 `renderWorkspaceHandoff.ts`，把路由 query 与当前项目解析为结构化交接状态。
2. 先在 `render-export-center.spec.ts` 写失败测试，覆盖匹配、项目不匹配、缺少 timelineId、普通进入 M14 四种状态。
3. 新增 `RenderWorkspaceHandoffCard.vue`，展示交接来源、项目、时间线和下一步。
4. 在 `RenderExportCenterPage.vue` 使用 `useRoute()` 与当前项目生成交接状态，并在摘要区前展示卡片。
5. 补 CSS，保证宽屏和紧凑窗口不遮挡任务列表。
6. 为 `RenderTask` 增加 nullable `timeline_id`，并让创建、DTO、前端类型保持一致。
7. 有效交接状态下，M14 创建任务时把 `timeline_id` 一并提交；任务详情展示时间线 ID。
8. 跑相关测试、构建和浏览器运行态验证。

## 验证

- `npm --prefix apps/desktop run test -- render-export-center.spec.ts`
- `npm --prefix apps/desktop run test -- workspace-export-readiness.spec.ts`
- `pytest tests/runtime/test_render_service.py tests/contracts/test_renders_runtime_contract.py`
- `npm --prefix apps/desktop run build`
- 浏览器检查 `/renders/export?from=workspace&projectId=project-1&timelineId=timeline-1`，确认交接卡存在、无控制台错误。

## 回退点

如 M14 页面出现布局或运行回归，只回退新增的 render handoff 模块、组件和 M14 页面接入代码；不影响 M05 已完成导出就绪卡。

如 `timeline_id` 契约出现数据库兼容问题，只回退本轮 RenderTask 字段、schema、DTO 和对应测试；不回退上一轮交接卡。
