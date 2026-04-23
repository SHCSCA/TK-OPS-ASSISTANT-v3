<template>
  <div class="page-container h-full" :data-review-state="reviewState">
    <header class="page-header">
      <div class="page-header__crumb">首页 / 优化与复盘</div>
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">{{ heroTitle }}</h1>
          <div class="page-header__subtitle">{{ heroSummary }}</div>
        </div>
        <div class="page-header__actions">
          <Chip :variant="projectTone">{{ projectLabel }}</Chip>
          <Chip :variant="summaryTone">{{ summaryLabel }}</Chip>
          <Chip :variant="analysisTone">{{ analysisLabel }}</Chip>
          <Button variant="secondary" :disabled="isBusy" @click="handleReload">
            <template #leading><span class="material-symbols-outlined">refresh</span></template>
            刷新摘要
          </Button>
          <Button
            variant="ai"
            data-action="analyze-review"
            :running="reviewStore.analyzing"
            :disabled="isBusy || !currentProjectId"
            @click="handleAnalyze"
          >
            <template #leading><span class="material-symbols-outlined">auto_awesome</span></template>
            生成复盘报告
          </Button>
        </div>
      </div>
    </header>

    <div v-if="feedbackMessage" class="dashboard-alert" :data-tone="feedbackTone">
      <span class="material-symbols-outlined">{{ feedbackTone === 'danger' ? 'error' : 'warning' }}</span>
      <span>{{ feedbackMessage }}</span>
    </div>

    <div class="workspace-grid">
      <main class="workspace-main">
        <Card class="detail-card h-full scroll-area">
          <div class="detail-card__header">
            <div>
              <p class="eyebrow">核心指标</p>
              <h3>复盘摘要</h3>
            </div>
            <Chip :variant="summaryTone">{{ summaryLabel }}</Chip>
          </div>
          <div class="detail-card__body no-padding">
            <div v-if="reviewState === 'loading'" class="empty-state">
              <span class="material-symbols-outlined spinning">sync</span>
              <strong>复盘数据加载中</strong>
              <p>正在从 Runtime 读取当前项目的复盘摘要。</p>
            </div>
            <div v-else-if="reviewState === 'blocked'" class="empty-state">
              <span class="material-symbols-outlined">block</span>
              <strong>缺少项目上下文</strong>
              <p>当前没有可用项目，复盘中心只能保持阻断态。</p>
              <Button variant="primary" @click="goToDashboard">返回总览</Button>
            </div>
            <div v-else-if="reviewState === 'error'" class="empty-state">
              <span class="material-symbols-outlined" style="color: var(--color-danger)">error</span>
              <strong>复盘摘要读取失败</strong>
              <p>{{ feedbackMessage }}</p>
            </div>
            <div v-else-if="reviewState === 'empty'" class="empty-state">
              <span class="material-symbols-outlined">insights</span>
              <strong>暂时没有复盘结论</strong>
              <p>当前摘要还没有分析结果，点击右上角按钮让 Runtime 读取真实复盘数据。</p>
            </div>
            <div v-else class="summary-content">
              <div class="kpi-grid">
                <div class="kpi-card">
                  <span>播放量</span>
                  <strong>{{ formatNumber(summary?.total_views || 0) }}</strong>
                  <p>真实统计</p>
                </div>
                <div class="kpi-card">
                  <span>点赞</span>
                  <strong>{{ formatNumber(summary?.total_likes || 0) }}</strong>
                  <p>真实统计</p>
                </div>
                <div class="kpi-card">
                  <span>评论</span>
                  <strong>{{ formatNumber(summary?.total_comments || 0) }}</strong>
                  <p>真实统计</p>
                </div>
                <div class="kpi-card">
                  <span>完播率</span>
                  <strong>{{ formatRate(summary?.completion_rate || 0) }}</strong>
                  <p>平均观看 {{ formatSeconds(summary?.avg_watch_time_sec || 0) }}</p>
                </div>
              </div>

              <div class="info-list">
                <div class="info-row">
                  <span>项目</span>
                  <strong>{{ summary?.project_name || summary?.project_id || "未命名" }}</strong>
                </div>
                <div class="info-row">
                  <span>最后分析</span>
                  <strong>{{ summary?.last_analyzed_at ? formatDate(summary.last_analyzed_at) : "尚未分析" }}</strong>
                </div>
                <div class="info-row">
                  <span>建议数量</span>
                  <strong>{{ visibleSuggestions.length }}</strong>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </main>

      <aside class="workspace-rail">
        <Card class="rail-card h-full scroll-area">
          <div class="rail-card__header">
            <div>
              <p class="eyebrow">行动面板</p>
              <h3>可执行优化</h3>
            </div>
            <Chip :variant="suggestionTone">{{ suggestionLabel }}</Chip>
          </div>
          <div class="rail-card__body no-padding">
            <div v-if="reviewState === 'loading'" class="empty-state small">
              <strong>建议加载中</strong>
              <p>建议列表会和摘要一起读取。</p>
            </div>
            <div v-else-if="reviewState === 'blocked'" class="empty-state small">
              <strong>没有建议可显示</strong>
              <p>先选中项目，复盘中心才会接收真实数据。</p>
            </div>
            <div v-else-if="reviewState === 'error'" class="empty-state small">
              <strong>建议暂不可用</strong>
              <p>先解决复盘摘要错误，再查看建议列表。</p>
            </div>
            <div v-else-if="visibleSuggestions.length === 0" class="empty-state small">
              <span class="material-symbols-outlined">check_circle</span>
              <strong>暂无优化建议</strong>
              <p>当前复盘没有需要处理的建议。</p>
            </div>
            <div v-else class="suggestion-list">
              <template v-for="(list, key) in categorizedSuggestions" :key="key">
                <div v-if="list.length > 0" class="suggestion-group">
                  <h4 class="group-title">{{ getCategoryTitle(key) }}</h4>
                  <div
                    v-for="suggestion in list"
                    :key="suggestion.id"
                    class="suggestion-card"
                    :data-tone="suggestion.priority"
                    data-review-suggestion
                  >
                    <div class="sugg-header">
                      <Chip size="sm" :variant="suggestion.priority === 'high' ? 'danger' : suggestion.priority === 'medium' ? 'warning' : 'success'">
                        {{ getPriorityLabel(suggestion.priority) }}
                      </Chip>
                      <span class="sugg-category">{{ suggestion.category }}</span>
                    </div>
                    <strong>{{ suggestion.title }}</strong>
                    <p>{{ suggestion.description }}</p>
                    
                    <div class="sugg-feedback" v-if="actionStates[suggestion.id]">
                      <span v-if="actionStates[suggestion.id] === 'generating'" class="feedback generating">
                        <span class="material-symbols-outlined spinning">sync</span> 执行中
                      </span>
                      <span v-else-if="actionStates[suggestion.id] === 'completed'" class="feedback completed">
                        <span class="material-symbols-outlined">check_circle</span> 已执行
                      </span>
                      <span v-else-if="actionStates[suggestion.id] === 'failed'" class="feedback failed">
                        <span class="material-symbols-outlined">error</span> 执行失败
                      </span>
                    </div>

                    <div class="sugg-actions">
                      <Button variant="ghost" size="sm" @click="handleIgnore(suggestion.id)">忽略</Button>
                      <Button
                        v-if="key !== 'record' && actionStates[suggestion.id] !== 'completed'"
                        :variant="key === 'immediate' ? 'primary' : 'secondary'"
                        size="sm"
                        :disabled="actionStates[suggestion.id] === 'generating'"
                        @click="handleAction(suggestion.id, suggestion.category)"
                      >
                        {{ getActionName(suggestion.category) }}
                      </Button>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </Card>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useProjectStore } from "@/stores/project";
import { useReviewStore } from "@/stores/review";

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

type SuggestionView = { category: string; description: string; id: string; priority: string; title: string; };
type ActionState = 'idle' | 'generating' | 'completed' | 'failed';

const reviewStore = useReviewStore();
const projectStore = useProjectStore();
const route = useRoute();
const router = useRouter();
const ignoredSuggestionIds = ref<string[]>([]);
const actionStates = ref<Record<string, ActionState>>({});

const currentProject = computed(() => projectStore.currentProject);
const currentProjectId = computed(() => currentProject.value?.projectId ?? "");
const summary = computed(() => reviewStore.summary);

const visibleSuggestions = computed<SuggestionView[]>(() =>
  (summary.value?.suggestions ?? []).filter((suggestion) => !ignoredSuggestionIds.value.includes(suggestion.code)).map((suggestion) => ({
    category: suggestion.category, description: suggestion.description, id: suggestion.code, priority: suggestion.priority, title: suggestion.title
  }))
);

const categorizedSuggestions = computed(() => {
  const immediate: SuggestionView[] = [];
  const next: SuggestionView[] = [];
  const record: SuggestionView[] = [];
  
  visibleSuggestions.value.forEach(s => {
    if (s.priority === 'high') immediate.push(s);
    else if (s.priority === 'medium') next.push(s);
    else record.push(s);
  });
  
  return { immediate, next, record };
});

const reviewState = computed(() => {
  if (projectStore.status === "loading" || reviewStore.loading || reviewStore.analyzing) return "loading";
  if (projectStore.error || reviewStore.error) return "error";
  if (!currentProjectId.value) return "blocked";
  if (!summary.value) return "loading";
  if (!summary.value.last_analyzed_at && visibleSuggestions.value.length === 0) return "empty";
  return "ready";
});

const projectLabel = computed(() => {
  if (projectStore.error) return "项目异常";
  if (!currentProjectId.value) return "待选项目";
  if (reviewState.value === "loading") return "项目读取中";
  return "项目已就绪";
});

const projectTone = computed(() => {
  if (projectStore.error) return "danger";
  if (!currentProjectId.value) return "warning";
  if (reviewState.value === "loading") return "brand";
  return "success";
});

const summaryLabel = computed(() => {
  if (reviewState.value === "loading") return "摘要读取中";
  if (reviewState.value === "empty") return "空态";
  if (reviewState.value === "error") return "错误";
  if (reviewState.value === "blocked") return "阻断";
  return "已就绪";
});

const summaryTone = computed(() => {
  if (reviewState.value === "error") return "danger";
  if (reviewState.value === "blocked" || reviewState.value === "empty") return "warning";
  if (reviewState.value === "loading") return "brand";
  return "success";
});

const analysisLabel = computed(() => {
  if (reviewState.value === "error") return "读取异常";
  if (reviewStore.analyzing) return "分析中";
  if (summary.value?.last_analyzed_at) return "已分析";
  if (reviewState.value === "blocked") return "待项目";
  return "待分析";
});

const analysisTone = computed(() => {
  if (reviewState.value === "error") return "danger";
  if (reviewStore.analyzing) return "brand";
  if (summary.value?.last_analyzed_at) return "success";
  if (reviewState.value === "blocked") return "warning";
  return "neutral";
});

const heroTitle = computed(() => {
  if (reviewState.value === "error") return "复盘数据读取异常";
  if (!currentProjectId.value) return "先选择一个项目，再进入复盘与优化";
  if (reviewState.value === "empty") return "复盘摘要已接入，但还没有分析结果";
  return `${currentProject.value?.projectName || "当前项目"} 的优化面板`;
});

const heroSummary = computed(() => {
  if (reviewState.value === "error") return "当前复盘数据读取失败，请先处理上方错误提示，再继续查看摘要和建议。";
  if (!currentProjectId.value) return "当前没有可用项目，复盘中心只能停留在阻断态。先回到总览创建或打开一个真实项目。";
  if (reviewState.value === "empty") return "复盘摘要来自 Runtime 真实接口。当前还没有分析结果，点击按钮后再读取真实指标与建议。";
  return "您可以针对不同的优化建议，一键执行系统级操作，自动修正和重构素材配置。";
});

const feedbackMessage = computed(() => {
  if (route.query.reason === "missing-project") return "当前没有项目上下文，复盘中心保持阻断态。";
  if (projectStore.error) return projectStore.error.requestId ? `${projectStore.error.message}（${projectStore.error.requestId}）` : projectStore.error.message;
  if (reviewStore.error) return reviewStore.error;
  return "";
});

const feedbackTone = computed(() => {
  if (projectStore.error || reviewStore.error) return "danger";
  if (route.query.reason === "missing-project") return "warning";
  return "neutral";
});

const suggestionLabel = computed(() => {
  if (reviewState.value === "loading") return "读取中";
  if (visibleSuggestions.value.length === 0) return "空态";
  return `${visibleSuggestions.value.length} 条待处理行动`;
});

const suggestionTone = computed(() => {
  if (reviewState.value === "loading") return "brand";
  if (visibleSuggestions.value.length === 0) return "neutral";
  return "success";
});

const isBusy = computed(() => reviewStore.loading || reviewStore.analyzing);

onMounted(() => { if (currentProjectId.value) void reviewStore.loadSummary(currentProjectId.value); });
watch(() => currentProjectId.value, (projectId) => { if (projectId) void reviewStore.loadSummary(projectId); });

async function handleAnalyze() { if (!currentProjectId.value) return; await reviewStore.analyze(currentProjectId.value); }
async function handleReload() { if (!currentProjectId.value) return; await reviewStore.loadSummary(currentProjectId.value); }
function handleIgnore(id: string) { ignoredSuggestionIds.value = [...ignoredSuggestionIds.value, id]; }
function goToDashboard() { void router.push("/dashboard"); }

function formatNumber(value: number) { return new Intl.NumberFormat("zh-CN").format(value); }
function formatRate(value: number) { return `${(value <= 1 ? value * 100 : value).toFixed(1)}%`; }
function formatSeconds(value: number) { return `${value.toFixed(1)} 秒`; }
function formatDate(value: string) { return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)); }

function getPriorityLabel(priority: string) {
  if (priority === "high") return "立即处理";
  if (priority === "medium") return "下轮处理";
  if (priority === "low") return "仅记录";
  return priority;
}

function getCategoryTitle(key: string | number) {
  if (key === 'immediate') return '立即处理 (Immediate Action)';
  if (key === 'next') return '下轮处理 (Next Iteration)';
  return '仅记录 (Record Only)';
}

function getActionName(category: string) {
  if (category.includes("文案") || category.includes("脚本") || category.includes("分镜") || category.includes("内容")) return "一键重新生成分镜";
  if (category.includes("系统") || category.includes("配置") || category.includes("设置")) return "调整系统配置";
  return "一键执行优化";
}

async function handleAction(id: string, category: string) {
  actionStates.value[id] = 'generating';
  try {
    // 模拟执行请求
    await new Promise(resolve => setTimeout(resolve, 1500));
    // 模拟随机失败
    if (Math.random() > 0.8) {
      actionStates.value[id] = 'failed';
    } else {
      actionStates.value[id] = 'completed';
    }
  } catch (e) {
    actionStates.value[id] = 'failed';
  }
}
</script>

<style scoped>
.page-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-8) var(--space-8);
  display: flex;
  flex-direction: column;
}

.page-header {
  display: grid;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-shrink: 0;
}

.page-header__crumb {
  font: var(--font-caption);
  letter-spacing: var(--ls-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.page-header__row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.page-header__title {
  font: var(--font-display-md);
  letter-spacing: var(--ls-display-md);
  color: var(--color-text-primary);
  margin: 0 0 4px 0;
}

.page-header__subtitle {
  font: var(--font-body-md);
  letter-spacing: var(--ls-body-md);
  color: var(--color-text-secondary);
}

.page-header__actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.dashboard-alert {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-muted);
  line-height: 1.6;
  margin-bottom: var(--space-4);
  font: var(--font-body-sm);
  display: flex;
  align-items: center;
  gap: 8px;
}

.dashboard-alert[data-tone="danger"] { border-color: rgba(255, 90, 99, 0.20); background: rgba(255, 90, 99, 0.08); color: var(--color-danger); }
.dashboard-alert[data-tone="warning"] { border-color: rgba(245, 183, 64, 0.20); background: rgba(245, 183, 64, 0.08); color: var(--color-warning); }
.dashboard-alert[data-tone="brand"] { border-color: rgba(0, 188, 212, 0.20); background: rgba(0, 188, 212, 0.08); color: var(--color-brand-primary); }

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.85fr);
  gap: var(--space-4);
  flex: 1;
  min-height: 0;
}

.workspace-main {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.workspace-rail {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  min-height: 0;
}

.h-full { height: 100%; }

.detail-card, .rail-card {
  padding: 0;
  display: flex;
  flex-direction: column;
}

.detail-card__header, .rail-card__header {
  padding: var(--space-5);
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-canvas);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.eyebrow {
  margin: 0 0 4px 0;
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
}

.detail-card__header h3, .rail-card__header h3 {
  margin: 0;
  font: var(--font-title-lg);
  color: var(--color-text-primary);
}

.detail-card__body, .rail-card__body {
  padding: var(--space-6);
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.detail-card__body.no-padding, .rail-card__body.no-padding {
  padding: 0;
}

.scroll-area { overflow-y: auto; }

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--space-10) var(--space-4);
  color: var(--color-text-tertiary);
  gap: 12px;
}

.empty-state.small {
  padding: var(--space-6);
  gap: 8px;
}

.empty-state .material-symbols-outlined {
  font-size: 40px;
  color: var(--color-text-secondary);
}

.empty-state strong {
  font: var(--font-title-md);
  color: var(--color-text-primary);
}

.empty-state p { margin: 0; font: var(--font-body-sm); line-height: 1.6; }

.spinning { animation: spin 1s linear infinite; }
@keyframes spin { 100% { transform: rotate(360deg); } }

.summary-content {
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}

.kpi-card {
  padding: var(--space-4);
  background: var(--color-bg-canvas);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.kpi-card span { font: var(--font-caption); color: var(--color-text-tertiary); }
.kpi-card strong { font: var(--font-display-md); color: var(--color-text-primary); }
.kpi-card p { margin: 0; font: var(--font-body-sm); color: var(--color-text-secondary); }

.info-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
}

.info-row span { font: var(--font-body-sm); color: var(--color-text-secondary); }
.info-row strong { font: var(--font-body-md); color: var(--color-text-primary); }

.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-5);
}

.suggestion-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.group-title {
  font: var(--font-title-sm);
  color: var(--color-text-secondary);
  margin: 0 0 4px 0;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--color-border-subtle);
}

.suggestion-card {
  padding: var(--space-4);
  background: var(--color-bg-canvas);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.suggestion-card[data-tone="high"] { border-color: rgba(255, 90, 99, 0.2); }
.suggestion-card[data-tone="medium"] { border-color: rgba(245, 183, 64, 0.2); }

.sugg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sugg-category {
  font: var(--font-caption);
  color: var(--color-text-tertiary);
}

.suggestion-card strong { font: var(--font-title-sm); color: var(--color-text-primary); }
.suggestion-card p { margin: 0; font: var(--font-body-sm); color: var(--color-text-secondary); line-height: 1.6; }

.sugg-feedback {
  margin-top: 4px;
  font: var(--font-caption);
  display: flex;
  align-items: center;
}

.feedback {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}

.feedback.generating {
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
}

.feedback.completed {
  background: rgba(0, 200, 83, 0.1);
  color: var(--color-success);
}

.feedback.failed {
  background: rgba(255, 90, 99, 0.1);
  color: var(--color-danger);
}

.feedback .material-symbols-outlined {
  font-size: 16px;
}

.sugg-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}

@media (max-width: 1180px) {
  .workspace-grid { grid-template-columns: 1fr; }
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 860px) {
  .page-header__row { flex-direction: column; }
}
</style>
