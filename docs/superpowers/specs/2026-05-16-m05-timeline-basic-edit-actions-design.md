# M05 时间线基础编辑动作设计

## 目标

本设计把 M05 时间线工具条从“视觉占位”推进到第一批真实编辑动作。当前只启用删除与分割，因为它们能显著提升基础剪辑可用性，同时可以在现有 Runtime 时间线模型内安全落地。

## 行为定义

### 删除片段

- 用户选中一个时间线片段后，“删除”按钮可用。
- 点击后调用 `DELETE /api/workspace/clips/{clip_id}`。
- Runtime 从所在轨道移除该片段，保存时间线并返回 `WorkspaceTimelineResultDto`。
- 前端刷新时间线，若原片段不存在，选中状态回退到当前轨道或空。

### 分割片段

- 用户选中一个时间线片段后，“分割”按钮可用。
- 默认分割点为片段内部中点；后续接入真实播放头后改为播放头位置。
- Runtime 调用 `POST /api/workspace/clips/{clip_id}/split`，请求体为 `{ "splitAtMs": number }`。
- `splitAtMs` 是时间线绝对毫秒位置，必须满足 `startMs < splitAtMs < startMs + durationMs`。
- Runtime 保留左片段原 ID，更新其 `durationMs/outPointMs`；新增右片段 ID 为 `{clip_id}-split-{splitAtMs}`，其 `startMs/durationMs/inPointMs/outPointMs` 与原片段连续。
- 同轨道片段按 `startMs` 排序，保持磁吸贴合。

## UI 规则

- “选择”和“磁吸”保持激活态。
- “分割 / 删除”在未选中片段时禁用。
- 执行中禁用工具按钮，避免重复请求。
- 错误进入页面统一错误态，显示中文可见反馈。
- 工具条只触发动作，不在组件内直接修改时间线数据。

## 边界

- 不实现撤销、拖拽、吸附算法、跨轨移动。
- 不删除锁定轨道内片段，Runtime 返回中文错误。
- 不分割小于 2ms 或分割点不在内部的片段。
- 不对真实媒体文件做切割，只更新时间线草稿模型。

