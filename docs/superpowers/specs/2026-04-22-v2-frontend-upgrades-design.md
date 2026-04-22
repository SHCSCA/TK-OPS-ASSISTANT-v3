# V2 Frontend Upgrades: Script Center & Video Deconstruction

## 1. Goal
Upgrade the Video Deconstruction Center to handle FFprobe unavailability and enhance the Script Center with better layout separation and status feedback.

## 2. Video Deconstruction Center (Bug F-08)

### 2.1 Problem
When FFprobe is missing, the system only shows a read-only fallback message. Users aren't guided on how to fix it or how to re-scan.

### 2.2 Solution
Show a prominent yellow alert bar when `error_code === 'media.ffprobe_unavailable'`.

### 2.3 UI Design
- **Component**: A new alert section above the main workspace.
- **Tone**: Warning (Yellow).
- **Content**:
    - **Reason**: "未检测到 FFprobe 可执行文件"
    - **Impact**: "时长 / 分辨率 / 码率字段暂无法解析"
    - **Actions**:
        - "查看修复指引": Links to the bootstrap/setup diagnostic page.
        - "重新扫描": Triggers backend detection (re-scans Runtime).

### 2.4 Technical Implementation
- Add a computed property `isFfprobeUnavailable` in `VideoDeconstructionCenterPage.vue`.
- Update `video-import` store to handle "re-scan" if the backend supports it, or just reload the videos.
- Add the alert UI with `v-if="isFfprobeUnavailable"`.

## 3. Script Center Upgrade (V2 Section 3.3)

### 3.1 Problem
The current layout is a 3-column grid that lacks clear visual separation between "Current Script", "Version Status", and "AI Actions". Version status and saving/generating feedback is not persistent enough.

### 3.2 Solution
- Re-layout the page to clearly group these three areas.
- Add a persistent version status bar.

### 3.3 UI Design
- **Three Core Areas**:
    1. **Current Script**: The central editor area.
    2. **Version Status**: The right sidebar (Version Trajectory).
    3. **AI Actions**: The left sidebar (Prompt Panel) and the AI Jobs area.
- **Persistent Version Status Bar**:
    - Location: Top of the editor card or a fixed bar at the bottom.
    - Statuses: "Generating" (AI Flow), "Saving" (Loading), "Saved" (Success), "Failed" (Error with Retry).
    - Content: Current Revision, Save Time, and Status Label.

### 3.4 Technical Implementation
- Update `ScriptTopicCenterPage.vue` layout.
- Add a new `StatusIndicator` component or integrate it into the `editor-header`.
- Ensure status transitions are smooth and visible.

## 4. Verification Plan
- **Bug F-08**: Mock `error_code: 'media.ffprobe_unavailable'` and verify the alert bar appears with correct buttons.
- **Script Center**: Verify the status bar updates correctly during "Generate" and "Save" actions. Verify the layout looks clean and separated.
