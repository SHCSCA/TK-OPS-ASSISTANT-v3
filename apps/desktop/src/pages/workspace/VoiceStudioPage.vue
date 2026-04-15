<template>
  <div class="voice-studio">
    <!-- 工具栏 -->
    <header class="studio-toolbar">
      <div class="toolbar-left">
        <span class="project-chip">
          {{ projectStore.currentProject?.projectName || '未选择项目' }}
        </span>
        <div class="speaker-select">
          <span class="material-symbols-outlined" style="font-size:18px">account_circle</span>
          <select v-model="store.config.speakerId">
            <option v-for="s in speakerOptions" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>
      </div>
      <button class="btn-primary" :disabled="isGenerating" @click="handleGenerate">
        <span class="material-symbols-outlined">{{ isGenerating ? 'sync' : 'settings_voice' }}</span>
        {{ isGenerating ? '生成中…' : '生成配音' }}
      </button>
    </header>

    <!-- 主区域 -->
    <main class="studio-main">
      <!-- 左：脚本段落 -->
      <aside class="script-panel">
        <div class="panel-header">脚本段落（{{ store.paragraphs.length }}）</div>
        <div v-if="store.status === 'loading'" class="empty-state">
          <span class="material-symbols-outlined">hourglass_empty</span>
          <span>加载中…</span>
        </div>
        <div v-else-if="store.paragraphs.length === 0" class="empty-state">
          <span class="material-symbols-outlined">article</span>
          <span>暂无脚本，请先在脚本中心创建内容</span>
        </div>
        <article
          v-for="(p, idx) in store.paragraphs"
          :key="idx"
          class="paragraph-card"
          :class="{ active: store.activeParagraphIndex === idx }"
          @click="store.activeParagraphIndex = idx"
        >
          <p class="paragraph-text">{{ p.text }}</p>
          <div class="paragraph-meta">预计时长：{{ p.estimatedDuration }}s</div>
        </article>
      </aside>

      <!-- 右：波形预览 -->
      <section class="preview-panel">
        <div class="waveform-container">
          <svg viewBox="0 0 960 100" class="waveform" preserveAspectRatio="none">
            <rect
              v-for="i in 80"
              :key="i"
              :x="i * 11.5"
              :y="50 - randomHeights[i] / 2"
              width="5"
              :height="randomHeights[i]"
              rx="2"
              :fill="`rgba(0,242,234,${0.25 + (i / 80) * 0.6})`"
            />
          </svg>
          <div class="preview-hint">
            <span class="material-symbols-outlined">waveform</span>
            生成配音后可在此预览音频
          </div>
        </div>

        <div class="player-controls">
          <button class="player-btn" @click="isPlaying = !isPlaying">
            <span class="material-symbols-outlined">{{ isPlaying ? 'pause' : 'play_arrow' }}</span>
          </button>
          <div class="progress-wrap">
            <div class="progress-bar">
              <div class="progress-filled" :style="{ width: progressPct + '%' }"></div>
              <div class="progress-handle" :style="{ left: progressPct + '%' }"></div>
            </div>
            <span class="time-display">00:00 / 00:00</span>
          </div>
        </div>
      </section>
    </main>

    <!-- 底部配置面板 -->
    <footer class="config-panel">
      <div class="config-group">
        <label>语速（{{ store.config.speed.toFixed(1) }}x）</label>
        <input type="range" v-model.number="store.config.speed" min="0.5" max="2.0" step="0.1" />
      </div>
      <div class="config-divider"></div>
      <div class="config-group">
        <label>音调（{{ store.config.pitch > 0 ? '+' : '' }}{{ store.config.pitch }}）</label>
        <input type="range" v-model.number="store.config.pitch" min="-50" max="50" step="1" />
      </div>
      <div class="config-divider"></div>
      <div class="config-group">
        <label>情绪风格</label>
        <div class="emotion-tags">
          <span
            v-for="e in emotionOptions"
            :key="e.id"
            class="tag"
            :class="{ active: store.config.emotion === e.id }"
            @click="store.config.emotion = e.id"
          >{{ e.name }}</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useProjectStore } from '@/stores/project';
import { useVoiceStudioStore } from '@/stores/voice-studio';

const projectStore = useProjectStore();
const store = useVoiceStudioStore();

const isPlaying = ref<boolean>(false);
const progressPct = ref<number>(0);

// Deterministic-looking random heights (seeded by index)
const randomHeights = Array.from({ length: 82 }, (_, i) =>
  Math.abs(Math.sin(i * 0.7) * 55 + Math.cos(i * 1.3) * 20 + 30)
);

const isGenerating = computed(() => store.status === 'generating');

const speakerOptions = [
  { id: 'xiaoxiao', name: '晓晓（温柔女声）' },
  { id: 'yunxi',    name: '云希（阳光男声）' },
  { id: 'xiaoyi',   name: '晓伊（活泼女声）' },
  { id: 'xiaoxuan', name: '晓萱（专业女声）' }
];

const emotionOptions = [
  { id: 'calm',   name: '平静' },
  { id: 'happy',  name: '欢快' },
  { id: 'news',   name: '播报' },
  { id: 'tender', name: '温柔' }
];

onMounted(async () => {
  const pid = projectStore.currentProject?.projectId;
  if (pid) {
    await store.load(pid);
  }
});

async function handleGenerate(): Promise<void> {
  await store.generate();
  if (store.status === 'error') {
    alert('生成失败：' + store.error?.message);
  }
}
</script>

<style scoped>
.voice-studio {
  display: grid;
  grid-template-rows: 44px 1fr 136px;
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
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.project-chip {
  background: var(--bg-card);
  color: var(--brand-primary);
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 20px;
  border: 1px solid rgba(0, 242, 234, 0.2);
}

.speaker-select {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-card);
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}

.speaker-select select {
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  cursor: pointer;
}

/* ── 主区域 ── */
.studio-main {
  display: grid;
  grid-template-columns: 300px 1fr;
  overflow: hidden;
}

/* 左：脚本 */
.script-panel {
  background: var(--bg-card);
  border-right: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  padding: 10px var(--spacing-md);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 13px;
  padding: var(--spacing-xl);
  text-align: center;
}

.script-panel > .empty-state + article,
.script-panel > article {
  overflow-y: auto;
}

.paragraph-card {
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: background 0.15s;
  border-left: 3px solid transparent;
}

.paragraph-card:hover {
  background: var(--bg-hover);
}

.paragraph-card.active {
  background: rgba(0, 242, 234, 0.06);
  border-left-color: var(--brand-primary);
}

.paragraph-text {
  font-size: 13px;
  line-height: 1.65;
  margin-bottom: 4px;
  color: var(--text-primary);
}

.paragraph-meta {
  font-size: 11px;
  color: var(--text-muted);
}

/* 右：波形 */
.preview-panel {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  padding: var(--spacing-lg) var(--spacing-xl);
  background: var(--bg-base);
  overflow: hidden;
}

.waveform-container {
  flex: 1;
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  overflow: hidden;
}

.waveform {
  width: 100%;
  height: 80px;
}

.preview-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

.player-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  background: var(--bg-card);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
  flex-shrink: 0;
}

.player-btn {
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s;
}

.player-btn:hover {
  background: var(--bg-hover);
}

.progress-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  min-width: 0;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: var(--border-default);
  border-radius: 2px;
  position: relative;
  cursor: pointer;
}

.progress-filled {
  height: 100%;
  background: var(--brand-primary);
  border-radius: 2px;
}

.progress-handle {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 12px;
  height: 12px;
  background: var(--text-primary);
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(0, 242, 234, 0.5);
}

.time-display {
  font-family: monospace;
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}

/* ── 配置面板 ── */
.config-panel {
  background: var(--bg-elevated);
  border-top: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: 0 var(--spacing-xl);
  overflow-x: auto;
}

.config-divider {
  width: 1px;
  height: 36px;
  background: var(--border-default);
  flex-shrink: 0;
}

.config-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
  min-width: 160px;
}

.config-group label {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.config-group input[type='range'] {
  accent-color: var(--brand-primary);
  width: 100%;
}

.emotion-tags {
  display: flex;
  gap: 6px;
}

.tag {
  padding: 3px 12px;
  border-radius: 20px;
  border: 1px solid var(--border-default);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  color: var(--text-secondary);
}

.tag:hover {
  border-color: var(--brand-primary);
  color: var(--brand-primary);
}

.tag.active {
  background: var(--brand-primary);
  border-color: var(--brand-primary);
  color: #000;
  font-weight: 600;
}

/* ── 按钮 ── */
.btn-primary {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--brand-primary);
  color: #000;
  border: none;
  padding: 7px 18px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.15s;
}

.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn-primary .material-symbols-outlined {
  font-size: 18px;
}
</style>
