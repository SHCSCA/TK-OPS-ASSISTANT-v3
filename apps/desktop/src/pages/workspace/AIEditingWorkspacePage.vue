<template>
  <ProjectContextGuard>
    <section class="workspace-page editing-workspace">
    <!-- 1. 顶部工具栏 -->
    <header class="editing-toolbar">
      <div class="editing-toolbar__actions">
        <button class="editing-toolbar__btn" title="选择">
          <span class="material-symbols-outlined">cursor_default</span>
        </button>
        <button class="editing-toolbar__btn" title="剪切">
          <span class="material-symbols-outlined">content_cut</span>
        </button>
        <button class="editing-toolbar__btn" title="缩放">
          <span class="material-symbols-outlined">zoom_in</span>
        </button>
        <button class="editing-toolbar__btn" title="撤销">
          <span class="material-symbols-outlined">undo</span>
        </button>
      </div>

      <div class="editing-toolbar__playback">
        <button class="editing-toolbar__btn" @click="handleSeek(-5)">
          <span class="material-symbols-outlined">replay_5</span>
        </button>
        <button class="editing-toolbar__btn editing-toolbar__btn--play" @click="togglePlay">
          <span class="material-symbols-outlined">{{ isPlaying ? 'pause' : 'play_arrow' }}</span>
        </button>
        <button class="editing-toolbar__btn" @click="handleSeek(5)">
          <span class="material-symbols-outlined">forward_5</span>
        </button>
        <span class="editing-toolbar__time">00:00 / 01:30</span>
      </div>

      <div class="editing-toolbar__status">
        <span class="page-chip">9:16</span>
        <button
          class="magic-cut-btn"
          :class="{ 'magic-cut-btn--loading': isAiGenerating }"
          :disabled="isAiGenerating"
          @click="handleAiMagicCut"
        >
          <span v-if="isAiGenerating" class="magic-cut-btn__spinner"></span>
          <span v-else class="material-symbols-outlined">auto_fix_high</span>
          AI 魔法剪
        </button>
      </div>
    </header>

    <!-- 2. 左侧素材面板 -->
    <aside class="asset-panel">
      <nav class="asset-panel__tabs">
        <button
          v-for="tab in assetTabs"
          :key="tab"
          class="asset-panel__tab"
          :class="{ 'asset-panel__tab--active': activeTab === tab }"
          @click="activeTab = tab"
        >
          {{ tab }}
        </button>
      </nav>

      <div class="asset-panel__list">
        <template v-if="activeTab === '视频'">
          <div v-for="v in videos" :key="v.id" class="asset-item" draggable="true">
            <div class="asset-item__thumb" :style="{ backgroundColor: v.color }"></div>
            <div class="asset-item__meta">
              <span class="asset-item__name">{{ v.name }}</span>
              <span class="asset-item__duration">{{ v.duration }}</span>
            </div>
          </div>
        </template>
        <template v-if="activeTab === '音频'">
          <div v-for="a in audios" :key="a.id" class="asset-item">
            <div class="asset-item__thumb asset-item__thumb--audio">
              <span class="material-symbols-outlined">audiotrack</span>
            </div>
            <div class="asset-item__meta">
              <span class="asset-item__name">{{ a.name }}</span>
              <span class="asset-item__duration">{{ a.duration }}</span>
            </div>
          </div>
        </template>
        <template v-if="activeTab === '字幕'">
          <div class="asset-panel__empty">暂无字幕素材</div>
        </template>
      </div>
    </aside>

    <!-- 3. 中央预览窗口 -->
    <main class="preview-window">
      <div class="preview-window__stage">
        <div class="preview-window__canvas">
          <div v-if="isPlaying" class="preview-window__playing-icon">
            <span class="material-symbols-outlined">play_circle</span>
          </div>
          <div class="preview-window__timecode">00:00:00:00</div>
        </div>
      </div>
    </main>

    <!-- 4. 右侧 AI 属性检查器 -->
    <aside class="ai-inspector">
      <h2 class="ai-inspector__title">AI 工具</h2>
      <div class="ai-inspector__tools">
        <div v-for="tool in aiTools" :key="tool.title" class="editor-card ai-tool-card">
          <h3 class="ai-tool-card__title">{{ tool.title }}</h3>
          <p class="ai-tool-card__desc">{{ tool.desc }}</p>
          <button class="settings-page__button ai-tool-card__btn" @click="runAiTool(tool.title)">
            {{ tool.action }}
          </button>
        </div>
      </div>
    </aside>

    <!-- 5. 时间线区域 -->
    <section class="timeline-editor" :class="{ 'timeline-editor--scanning': isAiGenerating }">
      <!-- 时间刻度轴 -->
      <div class="timeline-editor__ruler">
        <div class="timeline-editor__ruler-gutter"></div>
        <div class="timeline-editor__ruler-marks">
          <div v-for="i in 12" :key="i" class="ruler-mark">
            {{ String(i - 1).padStart(2, '0') }}:00
          </div>
        </div>
      </div>

      <!-- 轨道区域 -->
      <div class="timeline-editor__tracks">
        <div v-for="track in tracks" :key="track.id" class="track-row">
          <div class="track-row__label">
            <span class="material-symbols-outlined track-row__icon">{{ track.icon }}</span>
            <span class="track-row__name">{{ track.name }}</span>
          </div>
          <div
            class="track-row__blocks"
            @dragover.prevent="onTrackDragOver($event)"
            @dragleave="onTrackDragLeave($event)"
            @drop.prevent="onTrackDrop($event)"
          >
            <div
              v-for="block in track.blocks"
              :key="block.id"
              class="track-block"
              :style="{
                left: block.start + 'px',
                width: block.width + 'px',
                '--block-color': block.color
              }"
            >
              <span class="track-block__title">{{ block.name }}</span>
              <div class="track-block__actions">
                <button class="track-block__action-btn" title="剪切">
                  <span class="material-symbols-outlined">content_cut</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- AI 扫描线 -->
      <div v-if="isAiGenerating" class="timeline-editor__scan-line"></div>
    </section>

    <!-- 6. 时间线底栏 -->
    <footer class="timeline-footer">
      <div class="timeline-footer__stats">
        <span>FPS: 30</span>
        <span class="timeline-footer__sep">|</span>
        <span>总时长 00:01:30</span>
      </div>
      <div class="timeline-footer__zoom">
        <span class="material-symbols-outlined">zoom_out</span>
        <input
          v-model="zoomLevel"
          type="range"
          min="10"
          max="200"
          class="timeline-footer__zoom-slider"
        />
        <span class="material-symbols-outlined">zoom_in</span>
      </div>
    </footer>
    </section>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { ref } from "vue";
import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";

// ---- 状态 ----
const isAiGenerating = ref<boolean>(false);
const isPlaying = ref<boolean>(false);
const activeTab = ref<string>("视频");
const zoomLevel = ref<number>(50);

const assetTabs = ["视频", "音频", "字幕"] as const;

// ---- 静态数据 ----
interface VideoAsset {
  id: number;
  name: string;
  duration: string;
  color: string;
}
const videos: VideoAsset[] = [
  { id: 1, name: "素材_001.mp4", duration: "00:15", color: "#334155" },
  { id: 2, name: "背景延时.mov", duration: "00:30", color: "#475569" },
  { id: 3, name: "人物访谈.mp4", duration: "00:45", color: "#1e293b" }
];

interface AudioAsset {
  id: number;
  name: string;
  duration: string;
}
const audios: AudioAsset[] = [
  { id: 1, name: "BGM_鼓点.mp3", duration: "01:30" },
  { id: 2, name: "人声解说.wav", duration: "01:15" }
];

interface AiTool {
  title: string;
  desc: string;
  action: string;
}
const aiTools: AiTool[] = [
  { title: "自动转场", desc: "基于画面内容智能识别切分点并添加电影级转场效果", action: "立即分析" },
  { title: "AI 风格迁移", desc: "一键应用赛博朋克、复古胶片等视觉风格预设", action: "应用风格" },
  { title: "音频降噪", desc: "智能识别背景噪音并提取纯净人声轨道", action: "开始降噪" }
];

interface TrackBlock {
  id: string;
  name: string;
  start: number;
  width: number;
  color: string;
}
interface Track {
  id: string;
  name: string;
  icon: string;
  blocks: TrackBlock[];
}
const tracks: Track[] = [
  {
    id: "v2",
    name: "V2",
    icon: "subtitles",
    blocks: [{ id: "b1", name: "智能字幕", start: 50, width: 220, color: "rgba(245,158,11,0.85)" }]
  },
  {
    id: "v1",
    name: "V1",
    icon: "movie",
    blocks: [
      { id: "b2", name: "主画面 01", start: 0, width: 130, color: "rgba(0,242,234,0.85)" },
      { id: "b3", name: "转场片段", start: 132, width: 60, color: "rgba(0,220,215,0.7)" },
      { id: "b4", name: "主画面 02", start: 194, width: 160, color: "rgba(0,242,234,0.85)" }
    ]
  },
  {
    id: "a1",
    name: "A1",
    icon: "music_note",
    blocks: [{ id: "b5", name: "背景音乐", start: 0, width: 420, color: "rgba(16,185,129,0.75)" }]
  }
];

// ---- 交互 ----
async function handleAiMagicCut(): Promise<void> {
  isAiGenerating.value = true;
  await new Promise<void>((resolve) => setTimeout(resolve, 2200));
  isAiGenerating.value = false;
}

function togglePlay(): void {
  isPlaying.value = !isPlaying.value;
}

function handleSeek(seconds: number): void {
  void seconds;
}

function runAiTool(name: string): void {
  void name;
}

function onTrackDragOver(e: DragEvent): void {
  const target = e.currentTarget as HTMLElement;
  target.classList.add("track-row__blocks--dragover");
}

function onTrackDragLeave(e: DragEvent): void {
  const target = e.currentTarget as HTMLElement;
  target.classList.remove("track-row__blocks--dragover");
}

function onTrackDrop(e: DragEvent): void {
  const target = e.currentTarget as HTMLElement;
  target.classList.remove("track-row__blocks--dragover");
}
</script>

<style scoped>
/* ===== 根布局 ===== */
.editing-workspace {
  display: grid;
  grid-template-areas:
    "toolbar  toolbar   toolbar"
    "assets   preview   inspector"
    "timeline timeline  timeline"
    "timeline-footer timeline-footer timeline-footer";
  grid-template-columns: 280px 1fr 320px;
  grid-template-rows: 44px 1fr 240px 32px;
  height: 100%;
  overflow: hidden;
  background-color: var(--surface-primary);
  color: var(--text-primary);
}

/* ===== 工具栏 ===== */
.editing-toolbar {
  grid-area: toolbar;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background-color: var(--surface-secondary);
  border-bottom: 1px solid var(--border-default);
  gap: 16px;
  z-index: 10;
}

.editing-toolbar__actions,
.editing-toolbar__playback,
.editing-toolbar__status {
  display: flex;
  align-items: center;
  gap: 4px;
}

.editing-toolbar__btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background-color 160ms cubic-bezier(0.2, 0.8, 0.2, 1),
              color 160ms cubic-bezier(0.2, 0.8, 0.2, 1);
  font-size: 20px;
}

.editing-toolbar__btn:hover {
  background-color: var(--surface-tertiary);
  color: var(--text-primary);
}

.editing-toolbar__btn--play {
  background-color: var(--surface-sunken);
  color: var(--brand-primary);
  width: 36px;
  height: 36px;
  border-radius: 50%;
}

.editing-toolbar__time {
  font-size: 13px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  margin-left: 8px;
}

.magic-cut-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 14px;
  background-color: var(--brand-primary);
  color: #0a0f0f;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 220ms;
  white-space: nowrap;
}

.magic-cut-btn:hover {
  opacity: 0.9;
}

.magic-cut-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.magic-cut-btn__spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(0, 0, 0, 0.2);
  border-top-color: #000;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ===== 素材面板 ===== */
.asset-panel {
  grid-area: assets;
  background-color: var(--surface-secondary);
  border-right: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.asset-panel__tabs {
  display: flex;
  padding: 8px 8px 0;
  gap: 2px;
  border-bottom: 1px solid var(--border-default);
}

.asset-panel__tab {
  flex: 1;
  padding: 6px 4px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  cursor: pointer;
  border-radius: 4px 4px 0 0;
  transition: color 160ms, background-color 160ms;
}

.asset-panel__tab--active {
  color: var(--brand-primary);
  background-color: var(--surface-sunken);
  font-weight: 600;
}

.asset-panel__list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.asset-panel__empty {
  color: var(--text-secondary);
  font-size: 13px;
  text-align: center;
  padding: 32px 0;
}

.asset-item {
  display: flex;
  gap: 8px;
  padding: 8px;
  background-color: var(--surface-tertiary);
  border-radius: 8px;
  cursor: grab;
  transition: transform 160ms cubic-bezier(0.2, 0.8, 0.2, 1),
              box-shadow 160ms;
  border: 1px solid transparent;
}

.asset-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  border-color: var(--border-default);
}

.asset-item__thumb {
  width: 60px;
  height: 34px;
  border-radius: 4px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.asset-item__thumb--audio {
  background-color: var(--surface-sunken);
  color: var(--status-success);
}

.asset-item__meta {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  gap: 2px;
}

.asset-item__name {
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.asset-item__duration {
  font-size: 11px;
  color: var(--text-secondary);
}

/* ===== 预览窗口 ===== */
.preview-window {
  grid-area: preview;
  background-color: var(--surface-sunken);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  overflow: hidden;
}

.preview-window__stage {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-window__canvas {
  aspect-ratio: 9 / 16;
  height: 100%;
  max-width: 100%;
  background-color: #000;
  border-radius: 12px;
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.45);
  position: relative;
  overflow: hidden;
}

.preview-window__playing-icon {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.25);
  color: var(--brand-primary);
  font-size: 64px;
  animation: fadeIn 0.3s ease forwards;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

.preview-window__timecode {
  position: absolute;
  bottom: 14px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  background: rgba(0, 0, 0, 0.65);
  color: #fff;
  padding: 3px 10px;
  border-radius: 20px;
  letter-spacing: 0.05em;
}

/* ===== AI 属性检查器 ===== */
.ai-inspector {
  grid-area: inspector;
  background-color: var(--surface-secondary);
  border-left: 1px solid var(--border-default);
  padding: 16px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ai-inspector__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.ai-inspector__tools {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-tool-card {
  padding: 14px;
  border-radius: 10px;
  background-color: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ai-tool-card__title {
  font-size: 13px;
  font-weight: 600;
  margin: 0;
}

.ai-tool-card__desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
}

.ai-tool-card__btn {
  margin-top: 4px;
  font-size: 12px;
  padding: 6px 12px;
}

/* ===== 时间线区域 ===== */
.timeline-editor {
  grid-area: timeline;
  background-color: var(--surface-secondary);
  border-top: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.timeline-editor__ruler {
  height: 26px;
  display: flex;
  background-color: var(--surface-tertiary);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.timeline-editor__ruler-gutter {
  width: 52px;
  border-right: 1px solid var(--border-default);
  flex-shrink: 0;
}

.timeline-editor__ruler-marks {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.ruler-mark {
  min-width: 100px;
  font-size: 10px;
  color: var(--text-secondary);
  border-left: 1px solid var(--border-default);
  padding-left: 4px;
  display: flex;
  align-items: center;
  font-variant-numeric: tabular-nums;
}

.timeline-editor__tracks {
  flex: 1;
  overflow-y: auto;
}

.track-row {
  display: flex;
  height: 52px;
  border-bottom: 1px solid var(--border-default);
}

.track-row__label {
  width: 52px;
  flex-shrink: 0;
  background-color: var(--surface-sunken);
  border-right: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: var(--text-secondary);
}

.track-row__icon {
  font-size: 16px;
}

.track-row__name {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.track-row__blocks {
  flex: 1;
  position: relative;
  background-color: var(--surface-secondary);
  transition: background-color 160ms, border 160ms;
}

.track-row__blocks--dragover {
  background-color: rgba(0, 242, 234, 0.06);
  border: 1px dashed var(--brand-primary);
}

.track-block {
  position: absolute;
  top: 6px;
  bottom: 6px;
  border-radius: 5px;
  padding: 0 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: var(--block-color, var(--brand-primary));
  cursor: pointer;
  overflow: hidden;
  transition: filter 160ms;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.15);
}

.track-block:hover {
  filter: brightness(1.12);
}

.track-block__title {
  font-size: 11px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  pointer-events: none;
}

.track-block__actions {
  display: none;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  margin-left: 4px;
}

.track-block:hover .track-block__actions {
  display: flex;
}

.track-block__action-btn {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
  cursor: pointer;
  color: rgba(0, 0, 0, 0.7);
  font-size: 14px;
}

/* AI 扫描线 */
.timeline-editor__scan-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background-color: var(--brand-primary);
  box-shadow: 0 0 14px var(--brand-primary);
  pointer-events: none;
  z-index: 5;
  animation: scanAcross 2.2s linear infinite;
}

@keyframes scanAcross {
  from { left: 0%; }
  to   { left: 100%; }
}

.timeline-editor--scanning::after {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background-color: var(--brand-primary);
  box-shadow: 0 0 10px var(--brand-primary);
  z-index: 6;
}

/* ===== 时间线底栏 ===== */
.timeline-footer {
  grid-area: timeline-footer;
  background-color: var(--surface-secondary);
  border-top: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  font-size: 11px;
  color: var(--text-secondary);
}

.timeline-footer__stats {
  display: flex;
  align-items: center;
  gap: 12px;
}

.timeline-footer__sep {
  opacity: 0.3;
}

.timeline-footer__zoom {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 18px;
}

.timeline-footer__zoom-slider {
  width: 120px;
  accent-color: var(--brand-primary);
  cursor: pointer;
}

.material-symbols-outlined {
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
  font-size: inherit;
  line-height: 1;
  vertical-align: middle;
}
</style>
