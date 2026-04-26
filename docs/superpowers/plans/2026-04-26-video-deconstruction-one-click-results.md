# Video Deconstruction One-Click Results Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert video deconstruction into an explicit one-click workflow with a result panel styled around transcript, keyframes, and content structure.

**Architecture:** Runtime exposes a single orchestration endpoint that composes existing transcription, segmentation, and structure extraction services. The desktop page consumes Runtime through `runtime-client` and Pinia, while the UI remains a single video deconstruction page.

**Tech Stack:** Python FastAPI Runtime, Vue 3, Pinia, TypeScript, Vitest, Pytest.

---

### Task 1: Runtime One-Click API

**Files:**
- Modify: `apps/py-runtime/src/schemas/video_deconstruction.py`
- Modify: `apps/py-runtime/src/services/video_deconstruction_service.py`
- Modify: `apps/py-runtime/src/api/routes/video_deconstruction.py`
- Test: `tests/runtime/test_video_deconstruction_runtime_api.py`
- Test: `tests/contracts/test_video_deconstruction_api.py`

- [ ] Add `VideoDeconstructionResultDto` with transcript, segments, structure, and stages.
- [ ] Add `deconstruct_video(video_id)` to run transcription as optional, then segmentation and structure extraction.
- [ ] Change segmentation so missing transcription no longer blocks it.
- [ ] Add `POST /videos/{video_id}/deconstruct`.
- [ ] Assert that missing transcription Provider still returns succeeded segment and structure stages.

### Task 2: Desktop Runtime Adapter And Store

**Files:**
- Modify: `apps/desktop/src/types/runtime.ts`
- Modify: `apps/desktop/src/app/runtime-client.ts`
- Modify: `apps/desktop/src/stores/video-import.ts`
- Test: `apps/desktop/tests/video-deconstruction.spec.ts`

- [ ] Add `VideoDeconstructionResultDto` type.
- [ ] Add `deconstructVideo(videoId)` client call.
- [ ] Store transcript, segments, and structure by video ID.
- [ ] Add store action `deconstructVideoFile(videoId)` that refreshes result state and stages.

### Task 3: Video Deconstruction Result UI

**Files:**
- Modify: `apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue`
- Modify: `apps/desktop/src/pages/video/video-deconstruction-center.css`
- Test: `apps/desktop/tests/video-deconstruction.spec.ts`

- [ ] Add card action `开始拆解`.
- [ ] Add result panel with tabs `脚本文案`、`视频关键帧`、`内容解构`.
- [ ] Show missing transcript as a visible notice, not a blocking error.
- [ ] Keep stage status as compact progress, not the primary UI.
- [ ] Verify responsive layout remains usable in wide and compact windows.

### Task 4: Verification

**Commands:**
- `python -m pytest tests/runtime/test_video_deconstruction_runtime_api.py tests/contracts/test_video_deconstruction_api.py -q`
- `npm --prefix apps/desktop run test -- video-deconstruction.spec.ts`
- `npm --prefix apps/desktop run build`

**Expected:** All commands pass. If a warning is unrelated existing pytest config, record it without claiming it is fixed.
