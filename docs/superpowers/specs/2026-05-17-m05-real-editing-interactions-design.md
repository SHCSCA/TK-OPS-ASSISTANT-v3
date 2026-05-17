# M05 真实编辑交互设计

## 目标

本设计把 M05 AI 剪辑工作台从“按钮式基础编辑”推进到“鼠标级真实编辑交互”。本阶段聚焦基础剪辑闭环：片段可拖拽移动、边缘可拖拽裁剪、资产中心素材可加入或替换时间线、播放器和属性面板随当前选择联动、预检结果能定位到具体问题。

本阶段仍然不复制完整剪映功能，不做特效、转场、关键帧、复杂混音和真实媒体渲染。所有时间线修改仍以 Runtime 为唯一业务规则入口，前端只负责交互意图、预览态和可恢复错误反馈。

## 范围

允许实现：

- 同轨片段拖拽移动，拖动过程中显示预览位置。
- 左右边缘拖拽裁剪，拖动过程中显示预览时间范围。
- 磁吸到 0 点、播放头、相邻片段边界和轨道末尾。
- 资产中心素材加入时间线，支持按播放头或轨道末尾插入。
- 资产中心素材替换选中视频占位片段。
- 播放器、时间线、素材池和右侧属性面板同步当前片段上下文。
- 本地预检结果定位到轨道或片段，并提供可执行修复入口。

不做内容：

- 不做跨轨自由拖拽。
- 不做多选、组合、撤销、重做。
- 不做真实视频帧渲染和媒体文件切割。
- 不做复杂素材管理，M05 只消费 M09 资产中心。
- 不新增第 17 个页面，不回流旧壳。

## 架构

M05 三阶段采用“交互状态前端管理，业务结果 Runtime 落库”的结构。

- `WorkspaceTimeline.vue` 只负责轨道和片段渲染，事件委托给交互 composable。
- `workspaceTimelineViewModel.ts` 保留展示模型和纯计算；拖拽坐标、磁吸、裁剪预览拆到独立 helpers。
- `editing-workspace.ts` 只暴露业务动作：移动、裁剪、分割、删除、插入资产、替换片段、运行预检。
- Runtime 继续校验锁定轨道、负起点、同轨重叠、最小时长、素材状态和来源合法性。
- 页面级 `AIEditingWorkspacePage.vue` 只负责装配状态和组件事件，不直接拼业务规则。

## 交互模型

### 拖拽移动

用户按住片段主体并横向移动时，前端计算目标起点：

1. 从鼠标坐标转换为时间线绝对毫秒。
2. 保持片段原始时长不变。
3. 若磁吸开启，将起点吸附到候选点。
4. 渲染半透明预览片段和目标时间标签。
5. 松手后调用 `POST /api/workspace/clips/{clip_id}/move`。

Runtime 成功返回后刷新时间线；失败时清除预览态，保留原时间线，显示中文错误。

### 拖拽裁剪

用户拖动选中片段左右手柄时：

- 左手柄改变 `startMs`、`durationMs` 和 `inPointMs`。
- 右手柄只改变 `durationMs`。
- 前端预览态不能小于 500ms。
- 松手后调用 `POST /api/workspace/clips/{clip_id}/trim`。

Runtime 失败时恢复原片段显示，并提示具体原因。

### 资产加入和替换

资产 Tab 的主操作分两类：

- `加入时间线`：视频或图片进入视频轨，音频进入 BGM 或音频轨。默认插入到当前播放头；如果播放头处无法插入，则插入到目标轨道末尾。
- `替换选中片段`：仅在选中视频片段时可用，用资产素材替换占位来源，保持原片段时间范围。

前端不得根据文件路径自行判断素材可用性，必须使用 Runtime 返回的资产状态。不可用素材只能显示检查或转码入口，不允许直接入轨。

### 播放器和属性联动

- 选中视频片段：播放器显示 9:16 画面状态、来源、当前字幕覆盖。
- 选中音频片段：播放器显示音频来源和波形状态，不伪造可播放媒体。
- 选中字幕片段：播放器显示字幕安全区预览。
- 播放头移动：当前片段上下文随时间刷新。
- 右侧属性面板展示可编辑字段和只读字段，保存走 Runtime。

### 本地预检

预检结果从全局状态升级为可定位问题列表。每条问题必须包含：

- 严重度：阻断、警告、提示。
- 对象：轨道、片段或时间线。
- 中文说明。
- 可选修复动作：定位片段、打开资产 Tab、运行汇入、运行预检。

## 状态与异常

所有交互至少覆盖：

- 空状态：没有时间线、没有轨道、没有资产。
- 正常状态：片段可选择，可拖拽，可裁剪。
- 加载状态：资产同步、保存、预检运行中。
- 错误状态：Runtime 请求失败、素材不可用、轨道锁定、重叠、时长非法。
- 回滚状态：保存失败后恢复交互前时间线。

错误文案必须是中文，并保留用户可继续操作的上下文。

## 文件边界

新建或修改的前端边界：

- `apps/desktop/src/modules/workspace/workspaceTimelineGeometry.ts`：坐标、百分比、毫秒换算。
- `apps/desktop/src/modules/workspace/workspaceTimelineSnap.ts`：磁吸候选和吸附结果。
- `apps/desktop/src/modules/workspace/useWorkspaceTimelineDrag.ts`：拖拽移动和裁剪手势状态。
- `apps/desktop/src/modules/workspace/WorkspaceTimeline.vue`：接入拖拽 composable，不承载复杂计算。
- `apps/desktop/src/modules/workspace/WorkspaceAssetRail.vue`：资产加入和替换入口。
- `apps/desktop/src/modules/workspace/WorkspaceInspector.vue`：可编辑属性和预检定位入口。
- `apps/desktop/src/stores/editing-workspace.ts`：新增插入资产、替换资产、预检定位相关动作。
- `apps/desktop/src/types/runtime.ts`：新增资产入轨请求和预检问题定位类型。

Runtime 边界：

- `apps/py-runtime/src/schemas/workspace.py`：新增资产插入输入、预检问题定位字段。
- `apps/py-runtime/src/api/routes/workspace.py`：新增资产入轨接口。
- `apps/py-runtime/src/services/workspace_service.py`：新增插入素材到时间线、替换素材规则。

测试边界：

- `apps/desktop/tests/workspace-timeline-geometry.spec.ts`
- `apps/desktop/tests/workspace-timeline-drag.spec.ts`
- `apps/desktop/tests/workspace-asset-rail.spec.ts`
- `apps/desktop/tests/editing-workspace-store.spec.ts`
- `apps/desktop/tests/workspace-layout-contract.spec.ts`
- `tests/runtime/test_workspace_service.py`
- `tests/contracts/test_workspace_runtime_contract.py`

## 验收标准

- 宽屏和紧凑窗口下，时间线拖拽不挤压播放器和属性栏。
- 拖拽过程中有明确预览态，松手后 Runtime 保存。
- Runtime 失败可见、可恢复、不污染本地状态。
- 资产可从 M09 来源进入 M05 时间线，不在 UI 层拼接文件规则。
- 播放器、属性面板、素材池和时间线选中态一致。
- 预检问题可以定位到具体轨道或片段。
- 全量桌面测试、Runtime 重点测试、构建和 `git diff --check` 通过。

