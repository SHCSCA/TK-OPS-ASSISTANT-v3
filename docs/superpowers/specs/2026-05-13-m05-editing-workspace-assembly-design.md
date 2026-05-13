# M05 AI 剪辑工作台总装台设计

> 对应计划：`docs/superpowers/plans/2026-05-13-m05-editing-workspace-assembly.md`

## 目标

本次改造让 M05 AI 剪辑工作台成为项目创作结果的基础总装台。页面不再只是展示已有时间线草稿，而是可以把当前项目的脚本、分镜、配音轨和字幕轨汇入同一条真实时间线，并用接近剪映基础工作区的信息结构呈现：左上素材来源，中上播放器，右上基础属性，底部横向时间线。

本轮只做基础剪辑底座，不复制剪映完整功能。页面保留视频、音频、字幕三类基础轨道和片段选择、预检、后续切分扩展位；去掉贴纸、特效、滤镜、转场、动画、调节、模板商城、素材商店、关键帧、遮罩和复杂合成能力。

## 用户体验

- 顶部保留当前项目、时间线、当前选择和任务状态。
- 主按钮增加“汇入创作结果”，用于把脚本、分镜、配音和字幕同步到时间线。
- 辅助按钮增加“渲染前预检”，用于提前发现缺视频、缺音频、缺字幕、无效时长和时间线为空等问题。
- 工作区上半区采用三栏：
  - 左侧素材来源：显示脚本、分镜、配音、字幕的真实来源状态和段数。
  - 中间播放器：9:16 手机画幅，显示当前片段文案、字幕或来源摘要，不伪造真实视频播放。
  - 右侧基础属性：显示选中片段的来源、时间码、文本、视觉提示、状态和预检问题。
- 工作区中间有基础工具条，只放撤销、重做、切分、删除、缩放等基础剪辑预留按钮；本轮按钮禁用，不触发假操作。
- 底部时间线按视频轨、配音轨、字幕轨展示片段。选中轨道或片段后，播放器和属性栏同步更新。
- 缺少某个来源时不阻断汇入，页面显示“缺少配音轨”“缺少字幕轨”等可见问题，并允许后续重新汇入。

## 布局边界

参考剪映的是工作区结构，不是功能范围。

保留的信息结构：

```text
素材来源 | 9:16 播放器 | 基础属性
基础工具条
视频轨 / 配音轨 / 字幕轨
```

明确移除：

- 顶部大类入口：视频、音频、文本、贴纸、特效、转场、滤镜、调节。
- 素材市场、模板资源、复杂动画和高级特效参数。
- 多层复杂合成、关键帧、曲线、遮罩、专业调色和专业混音。

紧凑窗口下，上半区三栏折成单列，时间线仍保持在下方，避免播放器、属性栏和时间线互相挤压。

## 后端设计

新增 `WorkspaceAssemblyService`，避免继续膨胀现有 `WorkspaceService`。它只负责“汇入创作结果”，不处理片段移动、裁剪、替换、预览和预检。

新增接口：

```http
POST /api/workspace/projects/{project_id}/timeline/assemble
```

请求：

```json
{
  "mode": "merge_managed",
  "timelineName": "主时间线"
}
```

服务流程：

1. 读取当前项目最新时间线；没有则创建主时间线。
2. 读取最新脚本版本、最新分镜版本、最新 `ready` 配音轨、最新字幕轨。
3. 生成三条托管轨道：
   - `managed-video-storyboard`
   - `managed-audio-voice`
   - `managed-subtitle-track`
4. 保留非托管轨道和用户手动轨道。
5. 重新计算时间线时长和来源状态。
6. 保存时间线并返回 `WorkspaceTimelineResultDto`。

托管轨道可以被下次汇入覆盖，非托管轨道不可被覆盖。这样用户手工添加的基础片段不会被系统汇入动作误删。

## 汇入规则

脚本和分镜：

- 优先使用结构化脚本段落和结构化分镜场景。
- 每个分镜片段优先绑定同序号脚本段。
- 片段文本使用真实口播或字幕文案，不允许把 `S01 0-5s` 这类编号时间前缀写入片段文本。
- 分镜视频轨在没有真实视频资产时，片段 `sourceType` 使用 `manual` 或 `storyboard` 语义，状态显示为待生成或待替换，不伪造视频文件。

配音：

- 只自动使用最新 `status="ready"` 的配音轨。
- 配音轨片段沿用 `VoiceTrack.segments` 的 `startMs/endMs`，没有时间码时按脚本段顺序生成连续草稿时间。
- 音频片段 `sourceType="voice_track"`，`sourceId` 指向真实配音轨 ID。

字幕：

- 选择最新字幕轨，优先使用已有 `segments` 时间码。
- 字幕片段 `sourceType="subtitle_track"`，`sourceId` 指向真实字幕轨 ID。
- 字幕文本从字幕段 `text` 获取，不从旧脚本原文重新拆。

缺来源处理：

- 缺脚本：汇入结果为 `blocked`，提示先生成脚本。
- 缺分镜：仍可创建音频和字幕轨，但视频轨显示缺少分镜。
- 缺配音或字幕：不阻断，`assemblyState.issues` 记录对应问题。

## 数据与契约

扩展 `TimelineClipDto` 增加 `metadata`：

```json
{
  "sourceKind": "storyboard",
  "sourceRevision": 2,
  "segmentIndex": 0,
  "segmentId": "S01",
  "text": "真实片段文案",
  "visualPrompt": "基础画面建议"
}
```

扩展 `WorkspaceTimelineResultDto` 增加 `assemblyState`：

```json
{
  "status": "ready",
  "sources": [
    {
      "kind": "script",
      "status": "ready",
      "label": "脚本文案",
      "revision": 3,
      "trackId": null,
      "segmentCount": 5,
      "message": "已读取最新脚本版本。"
    }
  ],
  "issues": []
}
```

`saveState.source` 在汇入时固定为 `assembly`，用于前端提示“已汇入脚本、分镜、配音和字幕”。

## 前端设计

`editing-workspace` store 是唯一页面数据入口：

- `load(projectId)` 继续读取当前时间线。
- `assembleTimeline(projectId)` 调用新增汇入接口并刷新时间线、保存状态和来源状态。
- `runPrecheck()` 调用已有预检接口并保存预检结果。
- 所有异常继续走 `RuntimeRequestError`，页面显示中文错误，不暴露 traceback。

页面模块边界：

- `AIEditingWorkspacePage.vue` 只负责页面装配、按钮和 shell detail context。
- `WorkspaceAssetRail.vue` 只展示来源和片段入口。
- `WorkspacePreviewStage.vue` 只展示 9:16 手机预览和当前片段摘要。
- `WorkspaceTimeline.vue` 只展示轨道和片段，不在本轮做拖拽编辑。
- `WorkspaceInspector.vue` 只展示基础属性、来源、保存状态和预检问题。

样式以 `AIEditingWorkspacePage.css` 和模块 scoped CSS 承载，使用现有设计令牌和 CSS Variables，Light / Dark 都要可读。

## 异常与日志

- 后端汇入入口捕获仓储读取、JSON 解析和时间线保存异常，使用 `log.exception("汇入创作结果失败")` 记录，并返回中文 `HTTPException.detail`。
- 不把 traceback 暴露给前端。
- 缺配音、缺字幕、缺分镜属于业务问题，写入 `assemblyState.issues`，不作为 500。
- 前端 Runtime 失败进入页面错误态，并保留“刷新工作台”和“汇入创作结果”重试路径。
- 汇入成功后必须更新 `saveState`，让用户知道动作已完成。

## 测试

后端：

- `tests/runtime/test_workspace_assembly_service.py` 覆盖：
  - 最新脚本、分镜、配音、字幕汇入托管轨道。
  - 保留用户手动轨道。
  - 缺配音或字幕时生成 issues。
  - 汇入后 `saveState.source == "assembly"`。
- `tests/contracts/test_workspace_runtime_contract.py` 覆盖新增接口 JSON 信封和字段形状。

前端：

- `apps/desktop/tests/runtime-client-b-s4.spec.ts` 覆盖新增 Runtime client 路由。
- `apps/desktop/tests/editing-workspace-store.spec.ts` 覆盖 store 汇入和预检状态。
- `apps/desktop/tests/ai-editing-workspace-page.spec.ts` 覆盖按钮交互、来源状态、三类轨道和 9:16 预览。
- `apps/desktop/tests/workspace-layout-contract.spec.ts` 覆盖剪映式基础布局类名、9:16 预览和紧凑布局。

验证：

- `pytest tests/runtime/test_workspace_assembly_service.py tests/runtime/test_workspace_service.py tests/contracts/test_workspace_runtime_contract.py -q`
- `npm --prefix apps/desktop run test -- runtime-client-b-s4.spec.ts editing-workspace-store.spec.ts ai-editing-workspace-page.spec.ts workspace-layout-contract.spec.ts`
- `npm --prefix apps/desktop run build`
- 浏览器检查 `/workspace/editing` 点击汇入、预检和片段选择无控制台错误。

## 不做事项

- 不实现真实媒体播放。
- 不接入 AI 视频生成 Provider。
- 不实现剪映完整功能集。
- 不做贴纸、特效、滤镜、转场、动画、调节、模板商城和素材商店。
- 不做拖拽、多选、关键帧、遮罩、曲线或专业调色。
- 不改 M07 配音中心和 M08 字幕对齐中心的生成逻辑，只消费它们现有的真实轨道。

## 自查

- 范围聚焦 M05 总装台，未扩展第 17 个页面。
- 数据流保持 Runtime -> store -> page modules，不在 UI 层拼接业务规则。
- 异常、日志、状态反馈和重试路径有明确设计。
- 布局参考剪映基础结构，但复杂功能明确移除。
- 计划和设计均指向同一接口、同一 DTO 和同一测试集合。
