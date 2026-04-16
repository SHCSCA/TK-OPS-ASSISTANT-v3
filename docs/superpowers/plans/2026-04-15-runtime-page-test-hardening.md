# Runtime 页面测试硬化计划

## 背景

Batch 0 已经落地 TaskBus 与视频导入基线，M09-M15 也已有前端 store 与 Runtime route/service 骨架，但缺少系统化测试覆盖。当前风险集中在前后端契约、删除动作信封、store 错误态和后续模块开发的回归保护。

## 目标

- 为 M09-M15 现有 Runtime client、Pinia store 和后端 API 增加最小测试覆盖。
- 保持当前业务范围，不新增 M09-M15 的大功能。
- 修复测试暴露出的最小契约问题，尤其是 Runtime 统一 JSON 信封。

## 非目标

- 不实现 M09-M15 后续完整业务能力。
- 不重构页面视觉与布局。
- 不统一所有 DTO 命名策略。
- 不把自动化、发布、渲染、复盘全量接入 TaskBus。

## 文件地图

- 前端测试：`apps/desktop/tests/runtime-client-m09-m15.spec.ts`
- 前端 store 测试：`apps/desktop/tests/runtime-stores-m09-m15.spec.ts`
- 后端契约测试：`tests/contracts/test_runtime_page_modules_contract.py`
- 可能的最小修复：M09-M15 相关 stores 与 DELETE routes

## 验证

- `npm --prefix apps/desktop run test`
- `npm --prefix apps/desktop run build`
- `venv\Scripts\python.exe -m pytest tests\runtime -q`
- `venv\Scripts\python.exe -m pytest tests\contracts -q`
- `git diff --check`

## 回退点

如测试新增范围导致大面积业务重构需求，停止在测试硬化边界，不继续扩展模块功能；只保留已确认的契约修复或回滚对应测试草案。
