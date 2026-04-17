<template>
  <section class="review-page" :data-review-state="reviewState">
    <header class="review-hero" data-review-section="hero">
      <div class="review-hero__copy">
        <p class="review-hero__eyebrow">复盘与优化中心</p>
        <h1>{{ heroTitle }}</h1>
        <p class="review-hero__summary">{{ heroSummary }}</p>

        <div class="review-hero__badges">
          <span class="status-chip" :data-tone="projectTone">{{ projectLabel }}</span>
          <span class="status-chip" :data-tone="summaryTone">{{ summaryLabel }}</span>
          <span class="status-chip" :data-tone="analysisTone">{{ analysisLabel }}</span>
        </div>
      </div>

      <div class="review-hero__panel">
        <article class="review-mini-card">
          <p class="review-mini-card__label">当前项目</p>
          <strong>{{ currentProject?.projectName || "尚未选择" }}</strong>
          <p>{{ projectHint }}</p>
        </article>
        <article class="review-mini-card review-mini-card--accent">
          <p class="review-mini-card__label">最近分析</p>
          <strong>{{ summary?.last_analyzed_at ? formatDate(summary.last_analyzed_at) : "未分析" }}</strong>
          <p>{{ analysisHint }}</p>
        </article>
      </div>
    </header>

    <p v-if="feedbackMessage" class="review-alert" :data-tone="feedbackTone">
      {{ feedbackMessage }}
    </p>

    <div class="review-layout">
      <article class="review-card review-card--main" data-review-section="summary">
        <div class="review-card__header">
          <div>
            <p class="detail-panel__label">核心指标</p>
            <h2>复盘摘要</h2>
          </div>
          <span class="status-chip" :data-tone="summaryTone">{{ summaryLabel }}</span>
        </div>

        <div v-if="reviewState === 'loading'" class="review-empty">
          <strong>复盘数据加载中</strong>
          <p>正在从 Runtime 读取当前项目的复盘摘要。</p>
        </div>

        <div v-else-if="reviewState === 'blocked'" class="review-empty" data-review-blocked>
          <strong>缺少项目上下文</strong>
          <p>当前没有可用项目，复盘中心只能保持阻断态。</p>
          <button class="review-button" type="button" @click="goToDashboard">返回总览</button>
        </div>

        <div v-else-if="reviewState === 'error'" class="review-empty" data-review-error>
          <strong>复盘摘要读取失败</strong>
          <p>{{ feedbackMessage }}</p>
          <button class="review-button" type="button" :disabled="isBusy" @click="handleReload">
            重新读取
          </button>
        </div>

        <div v-else-if="reviewState === 'empty'" class="review-empty" data-review-empty>
          <strong>暂时没有复盘结论</strong>
          <p>当前摘要还没有分析结果，点击按钮让 Runtime 读取真实复盘数据。</p>
          <button class="review-button" type="button" data-action="analyze-review" :disabled="isBusy" @click="handleAnalyze">
            生成复盘报告
          </button>
        </div>

        <template v-else>
          <div class="review-kpis">
            <article class="review-kpi">
              <p class="review-kpi__label">播放量</p>
              <strong>{{ formatNumber(summary?.total_views || 0) }}</strong>
              <span>真实统计</span>
            </article>
            <article class="review-kpi">
              <p class="review-kpi__label">点赞</p>
              <strong>{{ formatNumber(summary?.total_likes || 0) }}</strong>
              <span>真实统计</span>
            </article>
            <article class="review-kpi">
              <p class="review-kpi__label">评论</p>
              <strong>{{ formatNumber(summary?.total_comments || 0) }}</strong>
              <span>真实统计</span>
            </article>
            <article class="review-kpi">
              <p class="review-kpi__label">完播率</p>
              <strong>{{ formatRate(summary?.completion_rate || 0) }}</strong>
              <span>平均观看 {{ formatSeconds(summary?.avg_watch_time_sec || 0) }}</span>
            </article>
          </div>

          <div class="review-summary-grid">
            <div class="review-summary-row">
              <span>项目</span>
              <strong>{{ summary?.project_name || summary?.project_id || "未命名" }}</strong>
            </div>
            <div class="review-summary-row">
              <span>最后分析</span>
              <strong>{{ summary?.last_analyzed_at ? formatDate(summary.last_analyzed_at) : "尚未分析" }}</strong>
            </div>
            <div class="review-summary-row">
              <span>建议数量</span>
              <strong>{{ visibleSuggestions.length }}</strong>
            </div>
          </div>

          <div class="review-actions">
            <button
              class="review-button"
              type="button"
              data-action="analyze-review"
              :disabled="isBusy || !currentProjectId"
              @click="handleAnalyze"
            >
              {{ reviewStore.analyzing ? "分析中" : "生成复盘报告" }}
            </button>
            <button class="review-button review-button--secondary" type="button" :disabled="isBusy" @click="handleReload">
              刷新摘要
            </button>
          </div>
        </template>
      </article>

      <aside class="review-card review-card--side" data-review-section="suggestions">
        <div class="review-card__header">
          <div>
            <p class="detail-panel__label">优化建议</p>
            <h2>AI 建议列表</h2>
          </div>
          <span class="status-chip" :data-tone="suggestionTone">{{ suggestionLabel }}</span>
        </div>

        <div v-if="reviewState === 'loading'" class="review-empty">
          <strong>建议加载中</strong>
          <p>建议列表会和摘要一起读取。</p>
        </div>

        <div v-else-if="reviewState === 'blocked'" class="review-empty">
          <strong>没有建议可显示</strong>
          <p>先选中项目，复盘中心才会接收真实数据。</p>
        </div>

        <div v-else-if="reviewState === 'error'" class="review-empty">
          <strong>建议暂不可用</strong>
          <p>先解决复盘摘要错误，再查看建议列表。</p>
        </div>

        <div v-else-if="visibleSuggestions.length === 0" class="review-empty">
          <strong>暂无优化建议</strong>
          <p>当前复盘摘要没有生成建议，保持空态即可。</p>
        </div>

        <div v-else class="review-suggestion-list">
          <article
            v-for="suggestion in visibleSuggestions"
            :key="suggestion.id"
            class="review-suggestion"
            :data-review-suggestion="suggestion.id"
            :data-tone="suggestion.priority"
          >
            <div class="review-suggestion__header">
              <span class="review-suggestion__badge">{{ getPriorityLabel(suggestion.priority) }}</span>
              <span class="review-suggestion__category">{{ suggestion.category }}</span>
            </div>
            <strong>{{ suggestion.title }}</strong>
            <p>{{ suggestion.description }}</p>
            <div class="review-suggestion__actions">
              <button class="review-link" type="button" @click="handleIgnore(suggestion.id)">忽略</button>
            </div>
          </article>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useProjectStore } from "@/stores/project";
import { useReviewStore } from "@/stores/review";

type SuggestionView = {
  category: string;
  description: string;
  id: string;
  priority: string;
  title: string;
};

type Tone = "neutral" | "brand" | "success" | "warning" | "danger" | "info";

const reviewStore = useReviewStore();
const projectStore = useProjectStore();
const route = useRoute();
const router = useRouter();
const ignoredSuggestionIds = ref<string[]>([]);

const currentProject = computed(() => projectStore.currentProject);
const currentProjectId = computed(() => currentProject.value?.projectId ?? "");
const summary = computed(() => reviewStore.summary);
const visibleSuggestions = computed<SuggestionView[]>(() =>
  (summary.value?.suggestions ?? [])
    .filter((suggestion) => !ignoredSuggestionIds.value.includes(suggestion.code))
    .map((suggestion) => ({
      category: suggestion.category,
      description: suggestion.description,
      id: suggestion.code,
      priority: suggestion.priority,
      title: suggestion.title
    }))
);

const reviewState = computed(() => {
  if (projectStore.status === "loading" || reviewStore.loading || reviewStore.analyzing) {
    return "loading";
  }

  if (projectStore.error || reviewStore.error) {
    return "error";
  }

  if (!currentProjectId.value) {
    return "blocked";
  }

  if (!summary.value) {
    return "loading";
  }

  if (!summary.value.last_analyzed_at && visibleSuggestions.value.length === 0) {
    return "empty";
  }

  return "ready";
});

const projectLabel = computed(() => {
  if (projectStore.error) return "项目异常";
  if (!currentProjectId.value) return "待选项目";
  if (reviewState.value === "loading") return "项目读取中";
  return "项目已就绪";
});

const projectTone = computed<Tone>(() => {
  if (projectStore.error) return "danger";
  if (!currentProjectId.value) return "warning";
  if (reviewState.value === "loading") return "info";
  return "success";
});

const summaryLabel = computed(() => {
  if (reviewState.value === "loading") return "摘要读取中";
  if (reviewState.value === "empty") return "空态";
  if (reviewState.value === "error") return "错误";
  if (reviewState.value === "blocked") return "阻断";
  return "已就绪";
});

const summaryTone = computed<Tone>(() => {
  if (reviewState.value === "error") return "danger";
  if (reviewState.value === "blocked") return "warning";
  if (reviewState.value === "empty") return "warning";
  if (reviewState.value === "loading") return "info";
  return "success";
});

const analysisLabel = computed(() => {
  if (reviewState.value === "error") return "读取异常";
  if (reviewStore.analyzing) return "分析中";
  if (summary.value?.last_analyzed_at) return "已分析";
  if (reviewState.value === "blocked") return "待项目";
  return "待分析";
});

const analysisTone = computed<Tone>(() => {
  if (reviewState.value === "error") return "danger";
  if (reviewStore.analyzing) return "info";
  if (summary.value?.last_analyzed_at) return "success";
  if (reviewState.value === "blocked") return "warning";
  return "neutral";
});

const heroTitle = computed(() => {
  if (reviewState.value === "error") {
    return "复盘数据读取异常";
  }

  if (!currentProjectId.value) {
    return "先选择一个项目，再进入复盘与优化";
  }

  if (reviewState.value === "empty") {
    return "复盘摘要已接入，但还没有分析结果";
  }

  return `${currentProject.value?.projectName || "当前项目"} 的复盘与优化面板`;
});

const heroSummary = computed(() => {
  if (reviewState.value === "error") {
    return "当前复盘数据读取失败，请先处理上方错误提示，再继续查看摘要和建议。";
  }

  if (!currentProjectId.value) {
    return "当前没有可用项目，复盘中心只能停留在阻断态。先回到总览创建或打开一个真实项目。";
  }

  if (reviewState.value === "empty") {
    return "复盘摘要来自 Runtime 真实接口。当前还没有分析结果，点击按钮后再读取真实指标与建议。";
  }

  return "这里展示的指标、建议和更新时间都来自 Runtime 的复盘摘要，不会伪造播放量或建议数量。";
});

const projectHint = computed(() => {
  if (reviewState.value === "error") {
    return "项目或复盘数据读取异常，暂时无法显示上下文。";
  }

  if (!currentProjectId.value) {
    return "没有项目上下文时，复盘中心不会拼接假结果。";
  }
  return `当前项目 ID ${currentProjectId.value}，复盘数据会按这个项目继续读取。`;
});

const analysisHint = computed(() => {
  if (reviewStore.analyzing) {
    return "正在生成真实复盘结果。";
  }

  if (summary.value?.last_analyzed_at) {
    return `最近分析 ${formatDate(summary.value.last_analyzed_at)}`;
  }

  return "尚未触发分析。";
});

const feedbackMessage = computed(() => {
  if (route.query.reason === "missing-project") {
    return "当前没有项目上下文，复盘中心保持阻断态。";
  }

  if (projectStore.error) {
    return projectStore.error.requestId
      ? `${projectStore.error.message}（${projectStore.error.requestId}）`
      : projectStore.error.message;
  }

  if (reviewStore.error) {
    return reviewStore.error;
  }

  return "";
});

const feedbackTone = computed<Tone>(() => {
  if (projectStore.error || reviewStore.error) return "danger";
  if (route.query.reason === "missing-project") return "warning";
  return "neutral";
});

const suggestionLabel = computed(() => {
  if (reviewState.value === "loading") return "读取中";
  if (visibleSuggestions.value.length === 0) return "空态";
  return `${visibleSuggestions.value.length} 条建议`;
});

const suggestionTone = computed<Tone>(() => {
  if (reviewState.value === "loading") return "info";
  if (visibleSuggestions.value.length === 0) return "neutral";
  return "brand";
});

const isBusy = computed(() => reviewStore.loading || reviewStore.analyzing);

onMounted(() => {
  if (currentProjectId.value) {
    void reviewStore.loadSummary(currentProjectId.value);
  }
});

watch(
  () => currentProjectId.value,
  (projectId) => {
    if (projectId) {
      void reviewStore.loadSummary(projectId);
    }
  }
);

async function handleAnalyze(): Promise<void> {
  if (!currentProjectId.value) return;
  await reviewStore.analyze(currentProjectId.value);
}

async function handleReload(): Promise<void> {
  if (!currentProjectId.value) return;
  await reviewStore.loadSummary(currentProjectId.value);
}

function handleIgnore(id: string): void {
  ignoredSuggestionIds.value = [...ignoredSuggestionIds.value, id];
}

function goToDashboard(): void {
  void router.push("/dashboard");
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("zh-CN").format(value);
}

function formatRate(value: number): string {
  const numeric = value <= 1 ? value * 100 : value;
  return `${numeric.toFixed(1)}%`;
}

function formatSeconds(value: number): string {
  return `${value.toFixed(1)} 秒`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function getPriorityLabel(priority: string): string {
  switch (priority) {
    case "high":
      return "高优先级";
    case "medium":
      return "中优先级";
    case "low":
      return "低优先级";
    default:
      return priority;
  }
}
</script>

<style scoped>
.review-page {
  display: grid;
  gap: var(--space-5);
}

.review-hero,
.review-card {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
}

.review-hero {
  display: grid;
  gap: var(--space-5);
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  padding: var(--space-8);
  background:
    linear-gradient(150deg, rgba(0, 188, 212, 0.10), transparent 40%),
    linear-gradient(320deg, rgba(112, 0, 255, 0.08), transparent 36%),
    var(--color-bg-surface);
}

.review-hero__copy h1,
.review-hero__copy p,
.review-mini-card p,
.review-alert,
.review-card__summary {
  margin: 0;
}

.review-hero__eyebrow {
  color: var(--color-brand-primary);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
}

.review-hero__copy h1 {
  margin-top: var(--space-3);
  font-size: 32px;
  line-height: 1.18;
  letter-spacing: -0.4px;
}

.review-hero__summary {
  margin-top: var(--space-4);
  max-width: 760px;
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.review-hero__badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-5);
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid transparent;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.status-chip[data-tone="success"] {
  background: rgba(34, 211, 154, 0.12);
  border-color: rgba(34, 211, 154, 0.18);
  color: var(--color-success);
}

.status-chip[data-tone="warning"] {
  background: rgba(245, 183, 64, 0.12);
  border-color: rgba(245, 183, 64, 0.18);
  color: var(--color-warning);
}

.status-chip[data-tone="danger"] {
  background: rgba(255, 90, 99, 0.12);
  border-color: rgba(255, 90, 99, 0.18);
  color: var(--color-danger);
}

.status-chip[data-tone="info"],
.status-chip[data-tone="brand"] {
  background: var(--color-bg-active);
  border-color: var(--color-border-subtle);
  color: var(--color-brand-primary);
}

.status-chip[data-tone="neutral"] {
  background: var(--color-bg-muted);
  border-color: var(--color-border-subtle);
  color: var(--color-text-secondary);
}

.review-hero__panel {
  display: grid;
  gap: var(--space-3);
}

.review-mini-card {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  background: var(--color-bg-canvas);
  border: 1px solid var(--color-border-subtle);
}

.review-mini-card--accent {
  background: linear-gradient(180deg, rgba(0, 188, 212, 0.05), rgba(112, 0, 255, 0.04));
}

.review-mini-card__label,
.review-kpi span,
.review-empty p,
.review-issue__body p,
.review-summary-row span {
  color: var(--color-text-secondary);
}

.review-mini-card strong {
  font-size: 18px;
  line-height: 1.35;
  word-break: break-word;
}

.review-alert {
  padding: var(--space-4) var(--space-5);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-muted);
  line-height: 1.6;
}

.review-alert[data-tone="danger"] {
  border-color: rgba(255, 90, 99, 0.20);
  background: rgba(255, 90, 99, 0.08);
  color: var(--color-danger);
}

.review-alert[data-tone="warning"] {
  border-color: rgba(245, 183, 64, 0.18);
  background: rgba(245, 183, 64, 0.08);
  color: var(--color-warning);
}

.review-layout {
  display: grid;
  gap: var(--space-4);
  grid-template-columns: minmax(0, 1.15fr) minmax(340px, 0.85fr);
  align-items: start;
}

.review-card {
  display: grid;
  gap: var(--space-4);
  padding: var(--space-5);
}

.review-card--main {
  min-height: 100%;
}

.review-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.review-card__header h2 {
  margin-top: 4px;
  font-size: 18px;
  line-height: 1.3;
}

.review-empty {
  display: grid;
  gap: 8px;
  padding: var(--space-5);
  border-radius: var(--radius-md);
  border: 1px dashed var(--color-border-default);
  background: var(--color-bg-canvas);
  text-align: center;
}

.review-empty p {
  line-height: 1.7;
}

.review-kpis {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.review-kpi {
  display: grid;
  gap: 4px;
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
}

.review-kpi__label {
  color: var(--color-text-tertiary);
  font-size: 12px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.review-kpi strong {
  font-size: 24px;
  line-height: 1.15;
}

.review-summary-grid {
  display: grid;
  gap: var(--space-3);
}

.review-summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 12px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
}

.review-summary-row strong {
  margin: 0;
  text-align: right;
}

.review-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.review-button,
.review-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 36px;
  padding: 0 var(--space-4);
  border: 0;
  border-radius: var(--radius-md);
  background: var(--color-brand-primary);
  color: var(--color-text-on-brand);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.review-button--secondary,
.review-link {
  background: transparent;
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-default);
}

.review-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.review-suggestion-list {
  display: grid;
  gap: var(--space-3);
}

.review-suggestion {
  display: grid;
  gap: 8px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
}

.review-suggestion[data-tone="high"] {
  border-color: rgba(255, 90, 99, 0.18);
}

.review-suggestion[data-tone="medium"] {
  border-color: rgba(245, 183, 64, 0.18);
}

.review-suggestion[data-tone="low"] {
  border-color: rgba(34, 211, 154, 0.18);
}

.review-suggestion__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.review-suggestion__badge,
.review-suggestion__category {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.review-suggestion__body strong,
.review-suggestion__body p,
.review-suggestion strong,
.review-suggestion p {
  margin: 0;
}

.review-suggestion p {
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.review-suggestion__actions {
  display: flex;
  gap: var(--space-2);
}

.review-issue__body {
  display: grid;
  gap: 6px;
}

.review-link {
  width: fit-content;
}

.review-card--side {
  min-height: 100%;
}

@media (max-width: 1180px) {
  .review-hero,
  .review-layout,
  .review-kpis {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .review-hero {
    padding: var(--space-5);
  }

  .review-card,
  .review-mini-card {
    padding: var(--space-4);
  }

  .review-summary-row {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
