# V2 Frontend Upgrades: Script Center & Video Deconstruction Implementation Plan

> **状态**：已落地（2026-04-22）。Task 1（F-08 FFprobe 降级提示）与 Task 2（脚本中心状态栏 + 3 栏布局）全部合入；`handleViewSetupGuide` / `handleConfigureProvider` 已从 `alert()` 占位改为 `router.push('/settings/ai-system', { query })` 真实跳转。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the Video Deconstruction Center to handle FFprobe unavailability and enhance the Script Center with better layout separation and status feedback.

**Architecture:** Use Vue 3 computed properties and existing Pinia stores to drive conditional UI components. Re-layout `ScriptTopicCenterPage.vue` for better modularity and add a persistent status indicator.

**Tech Stack:** Vue 3, TypeScript, Pinia, Tailwind CSS (via Vanilla CSS classes).

---

### Task 1: Fix Bug F-08 in VideoDeconstructionCenterPage.vue

**Files:**
- Modify: `apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue`
- Modify: `apps/desktop/src/stores/video-import.ts`

- [x] **Step 1: Add re-scan action to video-import store**

Modify `apps/desktop/src/stores/video-import.ts`:
```typescript
    async reScanRuntime(): Promise<void> {
      this.status = "loading";
      this.error = null;
      try {
        // Trigger a simple reload for now, as the backend will re-check FFprobe on next video load/import
        if (this.projectId) {
          await this.loadVideos(this.projectId);
        }
        this.status = "ready";
      } catch (error) {
        this.applyRuntimeError(error, "重新扫描 Runtime 失败。");
      }
    },
```

- [x] **Step 2: Add computed property and handler to VideoDeconstructionCenterPage.vue**

Modify `apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue`:
```typescript
const isFfprobeUnavailable = computed(() => {
  return videoImportStore.error?.details?.error_code === 'media.ffprobe_unavailable' || 
         videoImportStore.error?.message?.includes('FFprobe 不可用');
});

async function handleRescan(): Promise<void> {
  await videoImportStore.reScanRuntime();
}

function handleViewSetupGuide(): void {
  // Mock link to bootstrap/setup or AI settings diagnostic
  // For now, we can redirect to settings or just show a message
  alert("正在跳转至系统诊断页...");
}
```

- [x] **Step 3: Add the yellow alert bar to the template**

Modify `apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue`:
```html
      <div v-if="isFfprobeUnavailable" class="ffprobe-alert">
        <div class="ffprobe-alert__content">
          <span class="material-symbols-outlined">warning</span>
          <div class="ffprobe-alert__text">
            <strong>未检测到 FFprobe 可执行文件</strong>
            <p>影响范围：时长 / 分辨率 / 码率字段暂无法解析。请确保系统已安装 FFprobe。</p>
          </div>
        </div>
        <div class="ffprobe-alert__actions">
          <Button variant="secondary" size="sm" @click="handleViewSetupGuide">查看修复指引</Button>
          <Button variant="primary" size="sm" @click="handleRescan">重新扫描</Button>
        </div>
      </div>
```

- [x] **Step 4: Add styles for the alert bar**

Modify `apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue` `<style>`:
```css
.ffprobe-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  background: #FFFBE6;
  border: 1px solid #FFE58F;
  border-radius: var(--radius-md);
  margin-bottom: var(--space-6);
  color: #856404;
}

.ffprobe-alert__content {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
}

.ffprobe-alert__content .material-symbols-outlined {
  color: #FAAD14;
  font-size: 24px;
}

.ffprobe-alert__text strong {
  display: block;
  font: var(--font-title-sm);
  margin-bottom: 2px;
}

.ffprobe-alert__text p {
  margin: 0;
  font: var(--font-body-sm);
}

.ffprobe-alert__actions {
  display: flex;
  gap: var(--space-3);
}
```

### Task 2: Upgrade Script Center Layout & Status Bar

**Files:**
- Modify: `apps/desktop/src/pages/scripts/ScriptTopicCenterPage.vue`

- [x] **Step 1: Add Status Bar component logic**

Modify `apps/desktop/src/pages/scripts/ScriptTopicCenterPage.vue`:
```typescript
const statusLabel = computed(() => {
  if (scriptStore.status === 'generating') return "正在生成...";
  if (scriptStore.status === 'saving') return "正在保存...";
  if (scriptStore.status === 'ready') return "已保存";
  if (scriptStore.status === 'error') return "失败";
  return "就绪";
});

const statusTone = computed(() => {
  if (scriptStore.status === 'generating') return "brand";
  if (scriptStore.status === 'saving') return "info";
  if (scriptStore.status === 'ready') return "success";
  if (scriptStore.status === 'error') return "danger";
  return "default";
});
```

- [x] **Step 2: Add the persistent status bar to the template**

Modify `apps/desktop/src/pages/scripts/ScriptTopicCenterPage.vue`:
```html
    <!-- Add this above .script-workspace -->
    <div class="version-status-bar">
      <div class="status-item">
        <span class="status-dot" :data-tone="statusTone"></span>
        <strong>{{ statusLabel }}</strong>
      </div>
      <div class="status-divider"></div>
      <div class="status-item">
        <span>当前版本：</span>
        <strong>{{ revisionLabel }}</strong>
      </div>
      <div class="status-divider"></div>
      <div class="status-item">
        <span>最后更新：</span>
        <strong>{{ updatedAtLabel }}</strong>
      </div>
    </div>
```

- [x] **Step 3: Update Editor Header for better separation**

Modify `apps/desktop/src/pages/scripts/ScriptTopicCenterPage.vue` (Editor Card Header):
```html
             <div class="editor-header">
                <div class="header-main">
                   <h3>当前正文</h3>
                   <Chip variant="default" size="sm">{{ revisionLabel }}</Chip>
                </div>
                <div class="editor-tags">
                   <Chip v-if="currentSourceLabel">{{ currentSourceLabel }}</Chip>
                   <Chip v-if="currentModelLabel" variant="brand">{{ currentModelLabel }}</Chip>
                </div>
             </div>
```

- [x] **Step 4: Re-layout styles for 3-column modularity**

Modify `apps/desktop/src/pages/scripts/ScriptTopicCenterPage.vue` `<style>`:
```css
.version-status-bar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-2) var(--space-4);
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
  margin-bottom: var(--space-4);
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-text-tertiary);
}

.status-dot[data-tone="brand"] { background: var(--color-brand-primary); animation: pulse 2s infinite; }
.status-dot[data-tone="success"] { background: var(--color-success); }
.status-dot[data-tone="danger"] { background: var(--color-danger); }
.status-dot[data-tone="info"] { background: var(--color-info); }

.status-divider {
  width: 1px;
  height: 12px;
  background: var(--color-border-subtle);
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(var(--color-brand-primary-rgb), 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(var(--color-brand-primary-rgb), 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(var(--color-brand-primary-rgb), 0); }
}

.header-main {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
```

- [x] **Step 5: Ensure Script Workspace gap and alignment**

Modify `apps/desktop/src/pages/scripts/ScriptTopicCenterPage.vue` `<style>`:
```css
.script-workspace {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr) 320px;
  gap: var(--space-6); /* Increased gap for better separation */
  flex: 1;
  min-height: 0;
}
```
