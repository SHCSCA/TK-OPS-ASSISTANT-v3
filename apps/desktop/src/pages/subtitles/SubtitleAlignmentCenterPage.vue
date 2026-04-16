<template>
  <div class="subtitle-center">
    <!-- 工具栏 -->
    <header class="studio-toolbar">
      <div class="toolbar-left">
        <span class="toolbar-label">
          <span class="material-symbols-outlined" style="font-size:16px">subtitles</span>
          字幕对齐中心
        </span>
        <div class="scale-wrap">
          <span class="material-symbols-outlined" style="font-size:16px;color:var(--text-muted)">zoom_in</span>
          <input type="range" min="1" max="100" v-model.number="timelineScale" style="width:80px;accent-color:var(--brand-primary)" />
        </div>
      </div>
      <div class="toolbar-right">
        <button class="btn-secondary" @click="store.addSubtitle()">
          <span class="material-symbols-outlined">add</span>新增
        </button>
        <button class="btn-primary" :disabled="store.status === 'aligning'" @click="handleAlign">
          <span class="material-symbols-outlined">{{ store.status === 'aligning' ? 'sync' : 'auto_awesome' }}</span>
          {{ store.status === 'aligning' ? '对齐中…' : '自动对齐' }}
        </button>
        <button class="btn-outline">
          <span class="material-symbols-outlined">download</span>导出 SRT
        </button>
      </div>
    </header>

    <!-- 主区域 -->
    <main class="center-main">
      <!-- 左：视频预览 -->
      <div class="preview-area">
        <div class="video-placeholder">
          <span class="material-symbols-outlined" style="font-size:48px;color:var(--text-muted)">movie</span>
          <span style="color:var(--text-muted);font-size:13px">视频预览区</span>
        </div>
        <div class="subtitle-overlay" v-if="activeSubtitle">{{ activeSubtitle.text }}</div>
        <div class="video-controls">
          <button class="player-btn" @click="isPlaying = !isPlaying">
            <span class="material-symbols-outlined">{{ isPlaying ? 'pause' : 'play_arrow' }}</span>
          </button>
          <div class="video-progress">
            <div class="video-progress__bar">
              <div class="video-progress__fill" style="width:0%"></div>
            </div>
            <span style="font-size:11px;color:var(--text-muted);font-family:monospace">0:00 / 0:00</span>
          </div>
        </div>
      </div>

      <!-- 右：字幕列表 -->
      <aside class="subtitle-list">
        <div class="list-header">
          字幕条目（{{ store.subtitles.length }}）
        </div>
        <div class="list-body">
          <div v-if="store.subtitles.length === 0" class="empty-state">
            <span class="material-symbols-outlined">subtitles_off</span>
            <span>暂无字幕，点击自动对齐或手动新增</span>
          </div>
          <div
            v-for="(s, idx) in store.subtitles"
            :key="s.id"
            class="subtitle-item"
            :class="{ active: s.selected }"
            @click="store.selectSubtitle(idx)"
          >
            <div class="item-index">{{ idx + 1 }}</div>
            <div class="item-body">
              <span class="time-code">{{ formatTimecode(s.startMs) }} → {{ formatTimecode(s.endMs) }}</span>
              <input
                class="text-input"
                :value="s.text"
                placeholder="输入字幕内容…"
                @input="store.updateSubtitle(idx, { text: ($event.target as HTMLInputElement).value })"
                @click.stop
              />
            </div>
          </div>
        </div>
      </aside>
    </main>

    <!-- 底部时间轴 -->
    <footer class="timeline-area">
      <div class="timeline-ruler">
        <div v-for="i in 20" :key="i" class="ruler-tick">{{ (i - 1) * 5 }}s</div>
      </div>
      <div class="subtitle-track" :style="{ width: trackWidth + 'px' }">
        <div
          v-for="(s, idx) in store.subtitles"
          :key="s.id"
          class="subtitle-block"
          :class="{ active: s.selected }"
          :style="{
            left: (s.startMs / 1000 * pixelsPerSec) + 'px',
            width: Math.max(40, (s.endMs - s.startMs) / 1000 * pixelsPerSec) + 'px'
          }"
          @mousedown="handleBlockMouseDown(idx, $event)"
          @click="store.selectSubtitle(idx)"
        >
          <span>{{ s.text }}</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useProjectStore } from '@/stores/project';
import { useSubtitleAlignmentStore } from '@/stores/subtitle-alignment';
import { fetchImportedVideos } from '@/app/runtime-client';

const projectStore = useProjectStore();
const store = useSubtitleAlignmentStore();

const isPlaying = ref<boolean>(false);
const timelineScale = ref<number>(50);
const pixelsPerSec = computed<number>(() => 20 + timelineScale.value * 0.8);
const trackWidth = computed<number>(() => 20 * 5 * pixelsPerSec.value + 200);

const activeSubtitle = computed(() => store.subtitles.find((s) => s.selected) ?? null);

function formatTimecode(ms: number): string {
  const totalS = Math.floor(ms / 1000);
  const mill = ms % 1000;
  const min = Math.floor(totalS / 60);
  const sec = totalS % 60;
  return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')},${String(mill).padStart(3, '0')}`;
}

function handleBlockMouseDown(idx: number, e: MouseEvent): void {
  e.preventDefault();
  store.selectSubtitle(idx);
  const startX = e.clientX;
  const startMs = store.subtitles[idx].startMs;
  const duration = store.subtitles[idx].endMs - startMs;

  function onMouseMove(ev: MouseEvent): void {
    const deltaMs = Math.round(((ev.clientX - startX) / pixelsPerSec.value) * 1000);
    const newStart = Math.max(0, startMs + deltaMs);
    store.updateSubtitle(idx, { startMs: newStart, endMs: newStart + duration });
  }

  function onMouseUp(): void {
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
  }

  document.addEventListener('mousemove', onMouseMove);
  document.addEventListener('mouseup', onMouseUp);
}

async function handleAlign(): Promise<void> {
  await store.align();
  if (store.status === 'error') {
    alert('对齐失败：' + store.error?.message);
  }
}

onMounted(async () => {
  const pid = projectStore.currentProject?.projectId;
  if (pid) {
    try {
      const videos = await fetchImportedVideos(pid);
      if (videos.length > 0) {
        store.videoId = videos[0].id;
      }
    } catch {
      // 无导入视频时保持空态
    }
  }
});
</script>

<style scoped>
.subtitle-center {
  display: grid;
  grid-template-rows: 44px 1fr 180px;
  height: 100%;
  background: var(--bg-base);
  color: var(--text-primary);
  overflow: hidden;
}

/* ── 工具栏 ── */
.studio-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-md);
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.toolbar-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.scale-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* ── 主区域 ── */
.center-main {
  display: grid;
  grid-template-columns: 1fr 340px;
  overflow: hidden;
}

/* 视频预览 */
.preview-area {
  background: #000;
  margin: var(--spacing-md);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.video-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.subtitle-overlay {
  position: absolute;
  bottom: 48px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.65);
  color: #fff;
  font-size: 20px;
  padding: 4px 20px;
  border-radius: 4px;
  text-shadow: 0 2px 8px #000;
  white-space: nowrap;
  max-width: 90%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.video-controls {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 8px 12px;
  background: linear-gradient(0deg, rgba(0,0,0,0.7) 0%, transparent 100%);
}

.player-btn {
  background: rgba(255, 255, 255, 0.15);
  border: none;
  color: #fff;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}

.video-progress {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.video-progress__bar {
  flex: 1;
  height: 3px;
  background: rgba(255,255,255,0.2);
  border-radius: 2px;
  overflow: hidden;
}

.video-progress__fill {
  height: 100%;
  background: var(--brand-primary);
  border-radius: 2px;
}

/* 字幕列表 */
.subtitle-list {
  background: var(--bg-card);
  border-left: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.list-header {
  padding: 10px var(--spacing-md);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.list-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-sm);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: var(--spacing-xl);
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
  height: 100%;
}

.subtitle-item {
  display: flex;
  gap: 10px;
  padding: 10px;
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  margin-bottom: 6px;
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.subtitle-item:hover {
  background: var(--bg-hover);
}

.subtitle-item.active {
  border-color: var(--brand-primary);
  background: rgba(0, 242, 234, 0.05);
}

.item-index {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  min-width: 20px;
  padding-top: 2px;
}

.item-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.time-code {
  font-family: monospace;
  font-size: 10px;
  color: var(--brand-primary);
}

.text-input {
  background: transparent;
  border: none;
  border-bottom: 1px solid transparent;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  width: 100%;
  padding: 2px 0;
  transition: border-color 0.15s;
}

.text-input:focus {
  border-bottom-color: var(--brand-primary);
}

/* ── 时间轴 ── */
.timeline-area {
  background: var(--bg-elevated);
  border-top: 1px solid var(--border-default);
  overflow-x: auto;
  overflow-y: hidden;
  flex-shrink: 0;
}

.timeline-ruler {
  height: 22px;
  display: flex;
  border-bottom: 1px solid var(--border-subtle);
  user-select: none;
}

.ruler-tick {
  min-width: 50px;
  border-left: 1px solid var(--border-subtle);
  font-size: 10px;
  color: var(--text-muted);
  padding-left: 4px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.subtitle-track {
  position: relative;
  height: 60px;
  margin-top: 12px;
  min-height: 60px;
}

.subtitle-block {
  position: absolute;
  height: 40px;
  top: 0;
  background: rgba(255, 0, 80, 0.7);
  border: 1px solid var(--brand-secondary);
  border-radius: 4px;
  display: flex;
  align-items: center;
  padding: 0 8px;
  font-size: 11px;
  color: #fff;
  cursor: grab;
  user-select: none;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  transition: box-shadow 0.15s;
}

.subtitle-block:active {
  cursor: grabbing;
}

.subtitle-block.active {
  box-shadow: 0 0 0 2px var(--brand-primary);
  border-color: var(--brand-primary);
}

/* ── 按钮 ── */
.btn-primary {
  display: flex;
  align-items: center;
  gap: 5px;
  background: var(--brand-primary);
  color: #000;
  border: none;
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.15s;
}

.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn-secondary {
  display: flex;
  align-items: center;
  gap: 4px;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-secondary:hover {
  background: var(--bg-hover);
}

.btn-outline {
  display: flex;
  align-items: center;
  gap: 4px;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  cursor: pointer;
  transition: color 0.15s;
}

.btn-outline:hover {
  color: var(--text-primary);
}
</style>
