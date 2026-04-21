<template>
  <ProjectContextGuard>
    <div class="page-container">
      <header class="page-header">
        <div class="page-header__crumb">首页 / 策划中心</div>
        <div class="page-header__row">
          <div>
            <h1 class="page-header__title">分镜规划中心</h1>
            <div class="page-header__subtitle">分镜规划基于已采用的文案修订版本。当文案修订版更新时，请及时同步。</div>
          </div>
          <div class="page-header__actions">
            <!-- 视图切换 (mock) -->
            <div class="view-switch">
              <button class="view-btn is-active">列表视图</button>
              <button class="view-btn" disabled>大纲视图</button>
              <button class="view-btn" disabled>预览模式</button>
            </div>

            <Button v-if="isOutdated" variant="warning" :running="isBusy" @click="handleSync">
              <template #leading><span class="material-symbols-outlined">sync</span></template>
              同步最新文案
            </Button>
            <Button variant="ai" :running="isGenerating" :disabled="generateDisabled" @click="handleGenerate">  
              <template #leading><span class="material-symbols-outlined">auto_awesome</span></template>
              AI 生成分镜
            </Button>
            <Button variant="primary" :disabled="saveDisabled" @click="handleSave">
              <template #leading><span class="material-symbols-outlined">save</span></template>
              保存分镜
            </Button>
          </div>
        </div>
        
        <!-- 版本冲突警告横幅 -->
        <div v-if="isOutdated && !isBusy" class="outdated-banner">
          <span class="material-symbols-outlined">warning</span>
          <p>
            检测到当前项目有更新的文案版本 (v{{ scriptRevision }})。当前分镜仍基于 v{{ basedOnScriptRevision }}。
            建议在编辑前<strong>同步最新文案</strong>，以确保分镜逻辑一致。
          </p>
          <Button variant="secondary" size="sm" @click="handleSync">立即同步</Button>
        </div>
      </header>

      <div class="storyboard-workspace">
        <!-- 左侧 脚本对照区域 -->
        <aside class="storyboard-panel storyboard-panel--script">
          <Card class="storyboard-card h-full">
            <div class="storyboard-card__header">
              <h3>文案对照（只读）</h3>
              <Chip size="sm">{{ scriptSegments.length }} 段</Chip>
            </div>
            <div class="storyboard-card__body scroll-area no-padding">
              <div v-if="scriptSegments.length === 0" class="empty-text">
                当前项目尚无已采用的文案版本，请先前往脚本中心生成并采用脚本。
              </div>
              <div v-else class="segment-list">
                <div
                  v-for="segment in scriptSegments"
                  :key="segment.id"
                  class="segment-item"
                  :class="{ 'is-active': selectedSegmentId === segment.id }"
                  @click="selectedSegmentId = segment.id"
                >
                  <strong>{{ segment.title }}</strong>
                  <p>{{ segment.excerpt }}</p>
                </div>
              </div>
            </div>
          </Card>
        </aside>

        <!-- 中间 分镜规划工作台 -->
        <main class="storyboard-panel storyboard-panel--board">
          <Card class="storyboard-card h-full board-card" :class="{ 'is-generating': isGenerating }">
            <div class="ai-flow-bar" v-if="isGenerating"></div>

            <div class="board-header">
              <div class="board-header__copy">
                <h3>当前分镜面</h3>
                <span class="board-meta">{{ boardMeta }}</span>
              </div>
              <div class="board-tags">
                <Chip v-if="currentRevisionLabel !== '-'" :variant="isOutdated ? 'warning' : 'default'">
                  基于文案 v{{ basedOnScriptRevision }}
                </Chip>
                <Chip size="sm">{{ scenes.length }} 个分镜</Chip>
              </div>
            </div>

            <div class="board-body scroll-area bg-canvas">
              <div v-if="pageState === 'loading'" class="board-empty">
                <span class="material-symbols-outlined spinning">progress_activity</span>
                <p>正在拉取当前项目分镜详情...</p>
              </div>
              <div v-else-if="!hasScriptContent" class="board-empty">
                <span class="material-symbols-outlined">description</span>
                <p>文案内容为空<br/><small>分镜规划必须依赖有效的文案版本。请先在文案中心生成并采用文案。</small></p>
              </div>
              <div v-else-if="scenes.length === 0" class="board-empty">
                <span class="material-symbols-outlined">view_carousel</span>
                <p>当前项目还没有生成分镜脚本<br/><small>您可以点击右上角的 AI 生成分镜，或者等待 Runtime 自动同步文案变更后手动编辑。</small></p>
              </div>
            <div v-else class="scene-grid">
                <transition-group name="scene-list">
                  <div
                    v-for="(scene, index) in scenes"
                    :key="scene.sceneId"
                    class="scene-card"
                    :class="{ 'is-active': selectedSceneId === scene.sceneId }"
                    @click="selectedSceneId = scene.sceneId"
                  >
                    <div class="scene-header">
                      <div class="scene-header__title">
                        <Chip size="sm">分镜 {{ index + 1 }}</Chip>
                        <strong>{{ linkedSegmentTitle(index) }}</strong>
                      </div>
                    </div>

                    <div class="scene-fields">
                      <div class="form-group">
                        <Input v-model="scene.title" label="分镜标题" />
                      </div>
                      <div class="form-group">
                        <Input v-model="scene.summary" label="画面摘要" multiline :rows="2" />
                      </div>
                      <div class="form-group">
                        <Input v-model="scene.visualPrompt" label="视觉提示词" multiline :rows="3" />
                      </div>
                    </div>

                    <div class="scene-footer">
                       <span>{{ versionSourceLabel }}</span>
                       <span>{{ currentVersionTimestamp }}</span>
                    </div>
                  </div>
                </transition-group>
              </div>
            </div>
          </Card>
        </main>
      </div>
    </div>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import { useProjectStore } from "@/stores/project";
import { createRouteDetailContext, useShellUiStore } from "@/stores/shell-ui";
import { useScriptStudioStore } from "@/stores/script-studio";
import { useStoryboardStore } from "@/stores/storyboard";
import type { StoryboardScene } from "@/types/runtime";

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";
import Input from "@/components/ui/Input/Input.vue";

type PageState = "loading" | "empty" | "ready" | "error" | "blocked";

const projectStore = useProjectStore();
const scriptStudioStore = useScriptStudioStore();
const shellUiStore = useShellUiStore();
const storyboardStore = useStoryboardStore();

const scenes = ref<StoryboardScene[]>([]);
const selectedSceneId = ref<string | null>(null);
const selectedSegmentId = ref<string | null>(null);

const currentProjectId = computed(() => projectStore.currentProject?.projectId ?? "");
const projectName = computed(() => projectStore.currentProject?.projectName ?? "未选择项目");
const basedOnScriptRevision = computed(() => storyboardStore.document?.basedOnScriptRevision ?? 0);
const scriptRevision = computed(() => scriptStudioStore.document?.currentVersion?.revision ?? 0);
const isOutdated = computed(() => {
  if (basedOnScriptRevision.value === 0 || scriptRevision.value === 0) return false;
  return basedOnScriptRevision.value < scriptRevision.value;
});

const versions = computed(() => storyboardStore.document?.versions ?? []);
const recentJobs = computed(() => storyboardStore.document?.recentJobs ?? []);
const latestJob = computed(() => recentJobs.value[0] ?? null);
const currentVersion = computed(() => storyboardStore.document?.currentVersion ?? null);
const hasScenes = computed(() => scenes.value.length > 0);
const hasScriptContent = computed(
  () => (scriptStudioStore.document?.currentVersion?.content ?? "").trim().length > 0
);
const hasBlockedJob = computed(() => recentJobs.value.some((job) => job.status === "blocked"));
const isGenerating = computed(() => storyboardStore.status === "generating");
const isBusy = computed(
  () =>
    storyboardStore.status === "loading" ||
    storyboardStore.status === "saving" ||
    isGenerating.value
);

const pageState = computed<PageState>(() => {
  if (
    (storyboardStore.status === "loading" && !hasScenes.value) ||
    (scriptStudioStore.status === "loading" && !hasScriptContent.value)
  ) {
    return "loading";
  }
  if (storyboardStore.status === "error" || scriptStudioStore.status === "error") {
    return "error";
  }
  if (!hasScenes.value) {
    return hasBlockedJob.value ? "blocked" : "empty";
  }
  if (hasBlockedJob.value) {
    return "blocked";
  }
  return "ready";
});

const pageStateLabel = computed(() => {
  const map: Record<PageState, string> = { blocked: "能力阻断", empty: "空态", error: "错误", loading: "加载中", ready: "已就绪" };
  return map[pageState.value];
});

const pageStateDescription = computed(() => {
  if (pageState.value === "loading") return "正在通过真实运行时环境拉取文案对应的分镜规划结果和最近作业。";
  if (pageState.value === "error") return storyboardStore.error?.message ?? scriptStudioStore.error?.message ?? "分镜加载失败，请检查运行时状态。";
  if (pageState.value === "blocked") return latestJob.value?.error ?? "分镜生成任务被阻断，当前可手动调整规划逻辑。";
  if (pageState.value === "empty") return hasScriptContent.value ? "当前项目已具备文案，点击生成或同步以开始规划分镜。" : "分镜规划基于文案，请先前往脚本中心完成创作。";
  return "当前页面使用真实文案修订版和分镜模型生成的工作流反馈。";
});

const scriptSegments = computed(() =>
  parseScriptSegments(scriptStudioStore.document?.currentVersion?.content ?? "")
);

const selectedScene = computed(() =>
  scenes.value.find((scene) => scene.sceneId === selectedSceneId.value) ?? scenes.value[0] ?? null
);

const boardMeta = computed(() => {
  if (currentVersion.value) {
    return `基于文案 v${currentVersion.value.basedOnScriptRevision} 生成于 ${formatDateTime(currentVersion.value.createdAt)}`;
  }
  if (hasScriptContent.value) {
    return `当前文案 v${scriptRevision.value} 已就绪，请点击同步或生成分镜。`;
  }
  return "等待文案修订版同步以开始分镜规划。";
});

const currentRevisionLabel = computed(() => currentVersion.value?.revision ?? "-");
const currentRevisionDisplay = computed(() => currentVersion.value ? `修订 ${currentVersion.value.revision}` : "尚未生成分镜修订版");
const currentVersionTimestamp = computed(() => currentVersion.value ? formatDateTime(currentVersion.value.createdAt) : "尚未同步");
const versionSourceLabel = computed(() => currentVersion.value?.source ?? "本地规划");

const generateDisabled = computed(() => isBusy.value || !hasScriptContent.value);
const saveDisabled = computed(() => isBusy.value || scenes.value.length === 0);

watch(currentProjectId, (projectId, previousProjectId) => {
  if (!projectId || projectId === previousProjectId) return;
  selectedSceneId.value = null;
  selectedSegmentId.value = null;
  void storyboardStore.load(projectId);
  void scriptStudioStore.load(projectId);
}, { immediate: true });

watch(() => storyboardStore.document?.currentVersion?.scenes, (value) => {
  scenes.value = (value ?? []).map((scene) => ({ ...scene }));
  selectedSceneId.value = scenes.value[0]?.sceneId ?? null;
}, { immediate: true });

watch(scriptSegments, (value) => {
  selectedSegmentId.value = value[0]?.id ?? null;
}, { immediate: true });

watch([projectName, selectedScene, currentVersion, pageState, recentJobs, scriptSegments, isOutdated], () => {
  shellUiStore.setDetailContext(
    createRouteDetailContext("contextual", {
      icon: "view_timeline",
      eyebrow: "分镜规划中心",
      title: projectName.value,
      description: pageStateDescription.value,
      badge: {
        label: pageStateLabel.value,
        tone: pageState.value === "error" ? "danger" : isOutdated.value ? "warning" : "brand"      
      },
      metrics: [
        { id: "revision", label: "分镜修订版", value: currentRevisionDisplay.value },
        { id: "segments", label: "文案段落", value: String(scriptSegments.value.length) },
        { id: "scenes", label: "分镜数", value: String(scenes.value.length) }
      ],
      sections: [
        {
          id: "reference",
          title: "版本追踪",
          fields: [
            { id: "script", label: "文案版本", value: `v${basedOnScriptRevision.value}` + (isOutdated.value ? " (已过期)" : "") },
            { id: "scene", label: "当前选定分镜", value: selectedScene.value?.title ?? "未选择" }
          ]
        },
        {
          id: "jobs",
          title: "AI 生成作业",
          emptyLabel: "当前没有真实 AI 分镜生成记录。",
          items: recentJobs.value.slice(0, 3).map((job) => ({
            id: job.id,
            title: job.provider,
            description: job.model,
            meta: jobStatusLabel(job.status),
            tone: job.status === "blocked" ? "warning" : job.status === "failed" ? "danger" : "brand"
          }))
        }
      ]
    })
  );
}, { immediate: true });

onBeforeUnmount(() => {
  shellUiStore.clearDetailContext("contextual");
});

async function handleGenerate(): Promise<void> {
  await storyboardStore.generate();
}

async function handleSync(): Promise<void> {
  if (scenes.value.length > 0) {
    if (!confirm("同步最新文案将覆盖当前未保存的分镜改动。确定继续吗？")) return;
  }
  await storyboardStore.syncFromScript();
}

async function handleSave(): Promise<void> {
  const basedOnRevision = storyboardStore.document?.basedOnScriptRevision ?? scriptRevision.value;
  await storyboardStore.save(basedOnRevision, scenes.value);
}

function linkedSegmentTitle(index: number): string {
  return scriptSegments.value[index]?.title ?? `段落 ${index + 1}`;
}

function jobStatusLabel(status: string): string {
  if (status === "blocked") return "Blocked";
  if (status === "failed") return "失败";
  if (status === "running") return "运行中";
  if (status === "queued") return "排队中";
  if (status === "succeeded") return "已完成";
  return status;
}

function formatDateTime(value: string): string {
  if (!value) return "未知时间";
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit", hour12: false, minute: "2-digit", month: "numeric", day: "numeric"
  }).format(new Date(value));
}

function parseScriptSegments(value: string): Array<{ excerpt: string; id: string; title: string }> {
  return value.split(/\n\s*\n/).map((segment) => segment.trim()).filter(Boolean).map((segment, index) => {      
    const lines = segment.split("\n").map((line) => line.trim()).filter(Boolean);
    const rawTitle = lines[0] ?? `段落 ${index + 1}`;
    return {
      excerpt: lines.slice(1).join(" ").slice(0, 88) || "暂无文案正文，请先补充内容。",
      id: `segment-${index + 1}`,
      title: rawTitle.replace(/^#+\s*/, "")
    };
  });
}
</script>

<style scoped>
.page-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-8) var(--space-8);
  display: flex;
  flex-direction: column;
  height: 100%;
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

.view-switch {
  display: flex;
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
  padding: 2px;
  margin-right: var(--space-2);
}

.view-btn {
  background: transparent;
  border: none;
  border-radius: calc(var(--radius-md) - 2px);
  padding: 6px 12px;
  color: var(--color-text-secondary);
  font: var(--font-caption);
  font-weight: 600;
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--ease-standard), color var(--motion-fast) var(--ease-standard);
}

.view-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.view-btn.is-active {
  background: var(--color-bg-surface);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-sm);
}

.outdated-banner {
  margin-top: var(--space-4);
  background: color-mix(in srgb, var(--color-status-warning) 12%, transparent);
  border: 1px solid var(--color-status-warning);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.outdated-banner .material-symbols-outlined {
  color: var(--color-status-warning);
}

.outdated-banner p {
  flex: 1;
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-primary);
}

/* 布局网格 */
.storyboard-workspace {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: var(--space-4);
  flex: 1;
  min-height: 0;
}

.storyboard-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.h-full {
  height: 100%;
}

.storyboard-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.storyboard-card__header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--color-bg-canvas);
}

.storyboard-card__header h3 {
  margin: 0;
  font: var(--font-title-md);
  color: var(--color-text-primary);
}

.storyboard-card__body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
}

.storyboard-card__body.no-padding {
  padding: 0;
}

.scroll-area {
  overflow-y: auto;
}

.bg-canvas {
  background: var(--color-bg-canvas);
}

.empty-text {
  padding: var(--space-4);
  text-align: center;
  font: var(--font-body-sm);
  color: var(--color-text-tertiary);
}

/* Left Panel - Script Segments */
.segment-list {
  display: flex;
  flex-direction: column;
}

.segment-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--space-3) var(--space-4);
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--color-border-subtle);
  cursor: default;
  text-align: left;
  transition: background-color var(--motion-fast) var(--ease-standard);
}

.segment-item:hover {
  background: var(--color-bg-hover);
}

.segment-item.is-active {
  background: color-mix(in srgb, var(--color-brand-primary) 8%, transparent);
  border-left: 3px solid var(--color-brand-primary);
  padding-left: calc(var(--space-4) - 3px);
}

.segment-item strong {
  font: var(--font-title-sm);
  color: var(--color-text-primary);
}

.segment-item p {
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Right Panel - Scene Board */
.board-card {
  position: relative;
  background: var(--color-bg-surface);
  --motion-flow: 2.4s;
}

.ai-flow-bar {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--gradient-ai-primary);
  background-size: 200% 200%;
  animation: ai-flow var(--motion-flow) linear infinite;
  z-index: 10;
}

.board-header {
  padding: var(--space-4) var(--space-5);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-surface);
}

.board-header__copy h3 {
  margin: 0 0 4px 0;
  font: var(--font-title-lg);
  color: var(--color-text-primary);
}

.board-meta {
  font: var(--font-caption);
  color: var(--color-text-secondary);
}

.board-tags {
  display: flex;
  gap: var(--space-2);
}

.board-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  color: var(--color-text-tertiary);
  text-align: center;
  padding: var(--space-12) 0;
}

.board-empty .material-symbols-outlined {
  font-size: 32px;
  opacity: 0.5;
}

.board-empty p {
  margin: 0;
  font: var(--font-body-md);
  line-height: 1.5;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin { 100% { transform: rotate(360deg); } }

/* Scene Cards Waterfall */
.scene-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-4);
  padding: var(--space-5);
  align-items: flex-start;
}

.scene-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  cursor: pointer;
  transition: transform var(--motion-fast) var(--ease-spring), box-shadow var(--motion-fast) var(--ease-spring), border-color var(--motion-fast) var(--ease-standard);
  will-change: transform;
}

.scene-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.scene-card:active {
  transform: scale(0.98);
}

.scene-card.is-active {
  border-color: var(--color-brand-primary);
  box-shadow: 0 0 0 1px var(--color-brand-primary), var(--shadow-md);
  transform: translateY(-2px);
}

/* List Transitions */
.scene-list-move,
.scene-list-enter-active,
.scene-list-leave-active {
  transition: all var(--motion-default) var(--ease-spring);
}
.scene-list-enter-from,
.scene-list-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
.scene-list-leave-active {
  position: absolute;
}

.scroll-area {
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border-strong) transparent;
}

.scroll-area::-webkit-scrollbar {
  width: 4px;
}
.scroll-area::-webkit-scrollbar-thumb {
  background: var(--color-border-strong);
  border-radius: 99px;
}

.scene-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.scene-header__title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.scene-header__title strong {
  font: var(--font-title-sm);
  color: var(--color-text-primary);
}

.scene-fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.form-group {
  display: flex;
  flex-direction: column;
}

.scene-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--space-2);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-subtle);
  font: var(--font-caption);
  color: var(--color-text-tertiary);
}

@media (max-width: 960px) {
  .storyboard-workspace {
    grid-template-columns: 1fr;
  }
  .page-header__row {
    flex-direction: column;
  }
  .storyboard-panel--script {
    height: 240px;
    flex: none;
  }
}
</style>
