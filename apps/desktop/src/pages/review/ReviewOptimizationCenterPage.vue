<template>
  <ProjectContextGuard>
    <div class="review-center">
    <!-- 工具栏 -->
    <header class="review-toolbar">
      <div class="toolbar-left">
        <select class="project-select">
          <option value="">选择项目进行分析...</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <button class="btn-primary" @click="handleAnalyze">
          <span class="material-symbols-outlined">analytics</span>
          生成复盘报告
        </button>
      </div>
      <div class="toolbar-right">
        <div class="date-filter">
          <span class="material-symbols-outlined">calendar_today</span>
          <span>最近 7 天</span>
        </div>
      </div>
    </header>

    <main class="review-content">
      <!-- 左：统计概览 -->
      <section class="stats-overview">
        <div class="stats-grid">
          <div class="stat-card">
            <label>累计渲染</label>
            <div class="value">128</div>
            <div class="trend up">+12% vs 上周</div>
          </div>
          <div class="stat-card">
            <label>发布成功率</label>
            <div class="value">94.2%</div>
            <div class="trend up">+2.1%</div>
          </div>
           <div class="stat-card">
            <label>平均互动率</label>
            <div class="value">5.8%</div>
            <div class="trend down">-0.5%</div>
          </div>
        </div>

        <div class="chart-container">
          <div class="chart-header">
            <h4>流量与转换走势</h4>
            <div class="chart-legend">
              <span class="legend-item"><i class="dot primary"></i> 播放量</span>
              <span class="legend-item"><i class="dot secondary"></i> 互动量</span>
            </div>
          </div>
          <div class="chart-placeholder">
            <svg viewBox="0 0 500 200" class="mini-chart">
              <polyline
                fill="none"
                stroke="var(--brand-primary)"
                stroke-width="2"
                points="0,150 50,130 100,160 150,110 200,120 250,80 300,90 350,40 400,60 450,20 500,30"
              />
               <path d="M0,150 50,130 100,160 150,110 200,120 250,80 300,90 350,40 400,60 450,20 500,30 V200 H0 Z" fill="rgba(0,242,234,0.05)" />
            </svg>
            <div class="chart-hint">AI 正在根据历史渲染和发布数据生成洞察...</div>
          </div>
        </div>
      </section>

      <!-- 右：优化建议 -->
      <section class="suggestions-panel">
        <div class="panel-header">AI 优化建议 ({{ suggestions.length }})</div>
        <div v-if="suggestions.length === 0" class="empty-suggestions">
           <span class="material-symbols-outlined">auto_awesome</span>
           <p>暂无优化建议。选择项目并生成报告后，AI 将分析数据并给出改进方案。</p>
        </div>
        <div v-else class="suggestion-list">
          <div v-for="s in suggestions" :key="s.id" class="suggestion-card" :class="s.priority">
            <div class="suggestion-header">
              <span class="priority-icon material-symbols-outlined">
                {{ s.priority === 'high' ? 'priority_high' : 'info' }}
              </span>
              <span class="suggestion-title">{{ s.title }}</span>
              <span class="priority-tag">{{ getPriorityLabel(s.priority) }}</span>
            </div>
            <p class="suggestion-desc">{{ s.description }}</p>
            <div class="suggestion-actions">
              <button class="btn-apply" @click="handleApply(s.id)">应用建议</button>
              <button class="btn-ignore" @click="handleIgnore(s.id)">忽略</button>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import { fetchCurrentProjectContext } from '@/app/runtime-client';
import { useReviewStore } from '@/stores/review';

interface Suggestion {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low' | string;
}

const reviewStore = useReviewStore();
const currentProjectId = ref<string | null>(null);
const ignoredSuggestionIds = ref<string[]>([]);

const projects = computed(() =>
  reviewStore.summary
    ? [{ id: reviewStore.summary.project_id, name: reviewStore.summary.project_name ?? reviewStore.summary.project_id }]
    : []
);

const suggestions = computed<Suggestion[]>(() =>
  (reviewStore.summary?.suggestions ?? [])
    .filter((suggestion) => !ignoredSuggestionIds.value.includes(suggestion.code))
    .map((suggestion) => ({
      id: suggestion.code,
      title: suggestion.title,
      description: suggestion.description,
      priority: suggestion.priority
    }))
);

onMounted(async () => {
  const context = await fetchCurrentProjectContext();
  currentProjectId.value = context?.projectId ?? null;
  if (currentProjectId.value) await reviewStore.loadSummary(currentProjectId.value);
});

async function handleAnalyze(): Promise<void> {
  if (!currentProjectId.value) return;
  await reviewStore.analyze(currentProjectId.value);
}

function handleApply(id: string) {
  console.info('Apply review suggestion', id);
}

function handleIgnore(id: string) {
  ignoredSuggestionIds.value = [...ignoredSuggestionIds.value, id];
}

function getPriorityLabel(priority: string) {
  switch (priority) {
    case 'high': return '????';
    case 'medium': return '????';
    case 'low': return '??';
    default: return priority;
  }
}
</script>

<style scoped>
.review-center {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-base);
  color: var(--text-primary);
  overflow: hidden;
}

/* ── 工具栏 ── */
.review-toolbar {
  height: 44px;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-md);
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.project-select {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  outline: none;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--brand-primary);
  color: #000;
  border: none;
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.date-filter {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-card);
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
}

.date-filter .material-symbols-outlined {
  font-size: 16px;
}

/* ── 主内容 ── */
.review-content {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 380px;
  overflow: hidden;
}

/* 左：统计 */
.stats-overview {
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
  overflow-y: auto;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-lg);
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
}

.stat-card label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: 8px;
  display: block;
}

.stat-card .value {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 4px;
}

.trend {
  font-size: 11px;
}

.trend.up { color: #00ff88; }
.trend.down { color: var(--brand-secondary); }

.chart-container {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
}

.chart-header h4 {
  font-size: 14px;
  font-weight: 600;
}

.chart-legend {
  display: flex;
  gap: var(--spacing-md);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-secondary);
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.dot.primary { background: var(--brand-primary); }
.dot.secondary { background: var(--brand-secondary); }

.chart-placeholder {
  flex: 1;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.mini-chart {
  width: 100%;
  height: 200px;
}

.chart-hint {
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 12px;
}

/* 右：建议 */
.suggestions-panel {
  background: var(--bg-elevated);
  border-left: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  padding: 12px var(--spacing-md);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-subtle);
}

.suggestion-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.suggestion-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border-left: 4px solid #444;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.suggestion-card.high { border-left-color: var(--brand-secondary); }
.suggestion-card.medium { border-left-color: #ffaa00; }
.suggestion-card.low { border-left-color: #00ff88; }

.suggestion-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.priority-icon {
  font-size: 16px;
}

.high .priority-icon { color: var(--brand-secondary); }
.medium .priority-icon { color: #ffaa00; }
.low .priority-icon { color: #00ff88; }

.suggestion-title {
  font-size: 13px;
  font-weight: 600;
  flex: 1;
}

.priority-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(255,255,255,0.05);
  color: var(--text-muted);
}

.suggestion-desc {
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
}

.suggestion-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.suggestion-actions button {
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-apply {
  background: var(--brand-primary);
  color: #000;
  border: none;
  font-weight: 600;
}

.btn-ignore {
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border-subtle);
}

.btn-ignore:hover {
  border-color: var(--text-secondary);
  color: var(--text-secondary);
}

.empty-suggestions {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
  text-align: center;
  color: var(--text-muted);
  gap: 12px;
}

.empty-suggestions .material-symbols-outlined {
  font-size: 48px;
}

.empty-suggestions p {
  font-size: 13px;
}
</style>
