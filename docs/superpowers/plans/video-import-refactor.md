# 视频解构中心与导入引擎重构计划 (S 级任务)

## 1. 任务背景
当前视频解构中心（`VideoDeconstructionCenterPage.vue`）和导入服务（`video_import_service.py`）已跑通最小基线，但存在以下缺陷：
1. **视觉表现力不足**：Vanilla CSS 未能发挥双主题的潜力，缺乏 Unicorn.studio 或 React-bits 级别的高级交互反馈（如流光边框、玻璃态拟物、弹簧动效等）。
2. **同步阻塞风险**：视频导入与 FFprobe 元数据提取是同步 HTTP 请求，当导入大型视频或大量视频时，会直接违反 `CLAUDE.md` 铁律：“超过 2s 的操作禁止同步阻塞 HTTP”。
3. **缺少实时反馈通道**：系统尚无 WebSocket 层来推送后台长任务（Tasks）的状态变更。

## 2. 改造目标
实现“123 我都要”，并在 UI 质感上探索 CSS 与轻量级 WebGL 概念（景深、发光、材质）的极限缝合：
* **目标一：双主题与高级质感注入**。在 `index.css` / `tokens.css` 完善毛玻璃、流光动画、以及深浅模式的变量映射。
* **目标二：超拟真视频卡片**。结合 CSS 3D 景深效果、悬停流光边缘和流体骨架屏，重写 `VideoDeconstructionCenterPage.vue` 和 `video.css`。
* **目标三：异步导入引擎与 WebSocket**。在 Python Runtime 中实现内存级 `asyncio.Queue` 和全局 WebSocket 广播，将导入动作转为异步。

## 3. 执行拆解 (4 个 Phase)

### Phase 1: 设计令牌与基础架构改造 (UI 铁律)
- [ ] 修改 `tokens.css`：新增玻璃态背景色（`--glass-bg`）、高级投影（`--shadow-glow`）、品牌色脉冲光晕等。
- [ ] 修改 `index.css`：注册全局动画类（如 `@keyframes shimmer`、`@keyframes float`），确保双主题无缝切换。

### Phase 2: 视频解构中心 UI 蜕变 (前端重构)
- [ ] 重写 `video.css`：引入炫酷的视频卡片样式（内发光边框、毛玻璃面板、Hover 3D 轻微悬浮）。
- [ ] 改造 `VideoDeconstructionCenterPage.vue`：
  - [ ] 增加骨架屏/占位符动效（解析中状态）。
  - [ ] 微型数据可视化标签（FPS、分辨率颜色映射）。
  - [ ] 右侧 `Detail Panel`（可选：如果时间允许，加入点击卡片展出右侧抽屉预览详情）。

### Phase 3: Python WebSocket 引擎 (架构铁律)
- [ ] 新建 `apps/py-runtime/src/api/routes/ws.py`，实现 FastAPI 的 WebSocket Endpoint。
- [ ] 新建 `apps/py-runtime/src/services/ws_manager.py`，管理全局连接池并提供 `broadcast()` 方法。
- [ ] 在 `factory.py` 注册 WebSocket 路由。

### Phase 4: 异步视频处理任务流 (流程铁律)
- [ ] 新建 `apps/py-runtime/src/tasks/video_tasks.py`，实现 `asyncio` 的后台 FFprobe 处理逻辑。
- [ ] 修改 `video_import_service.py`：
  - HTTP `POST /import` 改为**仅存库并返回 "imported" 状态**，立即释放 HTTP 阻塞。
  - 将文件路径投递给 `video_tasks` 进行后台 FFprobe 探测。
  - 探测完成后，更新 SQLite 状态，并通过 `ws_manager` 推送 `{ "event": "video_ready", "video_id": "..." }`。
- [ ] 修改前端 `video-import.ts`：监听 WebSocket，收到 `video_ready` 或 `video_error` 时自动更新视频列表状态。

## 4. 验收标准 (证据驱动)
1. **测试通过**：运行 `npm run test` (Python `pytest`) 确保重构未破坏已有契约测试。
2. **异步证明**：前端网络面板截图/终端输出证明 `/import` 接口耗时在 100ms 内，真实元数据通过 WS 延迟到达。
3. **视觉证明**：UI 在 Light 和 Dark 模式下悬停视频卡片具备高品质动态反馈。
