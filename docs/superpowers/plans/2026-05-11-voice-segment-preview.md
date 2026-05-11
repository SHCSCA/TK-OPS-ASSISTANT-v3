# Voice Segment Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 配音中心支持整段预览与当前段落预览，且不增加 TTS 调用次数。

**Architecture:** 前端播放器继续使用 Runtime 音频流地址。新增一个段落区间计算 helper，根据脚本段落估算时长生成音频切片范围，并在播放器的 `play/timeupdate/loadedmetadata` 事件中控制当前段落播放边界。后端不新增段落音频文件，不改变现有 VoiceTrack 生成主链路。

**Tech Stack:** Vue 3、Pinia、Vitest、现有 Runtime HTTP 音频流接口。

---

### Task 1: 段落区间计算

**Files:**
- Create: `apps/desktop/src/modules/voice/voice-preview-ranges.ts`
- Test: `apps/desktop/tests/voice-preview-ranges.spec.ts`

- [ ] 写失败测试：给定 3 个段落估算时长和 10 秒真实音频时长，返回缩放后的区间。
- [ ] 实现 `buildVoicePreviewRanges` 与 `formatPreviewTime`。
- [ ] 运行 `npm --prefix apps/desktop run test -- voice-preview-ranges.spec.ts`。

### Task 2: 播放器模式切换

**Files:**
- Modify: `apps/desktop/src/modules/voice/VoicePreviewStage.vue`
- Modify: `apps/desktop/src/pages/voice/VoiceStudioPage.vue`
- Test: `apps/desktop/tests/voice-studio-page.spec.ts`

- [ ] 写失败测试：页面显示 `整段` / `当前段落` 切换，切到当前段落后展示当前段落范围。
- [ ] 给 `VoicePreviewStage` 传入 `paragraphs` 与 `activeParagraphIndex`。
- [ ] 在播放器中实现整段模式与段落模式；段落模式在播放时跳到当前段起点，到当前段终点自动暂停。
- [ ] 运行 `npm --prefix apps/desktop run test -- voice-studio-page.spec.ts voice-preview-ranges.spec.ts`。

### Task 3: 验证

**Files:**
- Verify only.

- [ ] 运行 `npm --prefix apps/desktop run test -- runtime-client-voice.spec.ts voice-studio-page.spec.ts voice-preview-ranges.spec.ts`。
- [ ] 运行 `npm --prefix apps/desktop run build`。
- [ ] 运行 `git diff --check`。
