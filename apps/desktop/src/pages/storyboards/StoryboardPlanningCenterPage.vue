<template>
  <ProjectContextGuard>
    <div class="page-container">
      <header class="page-header">
        <div class="page-header__crumb">首页 / 分镜规划中心</div>
        <div class="page-header__row">
          <div>
            <h1 class="page-header__title">分镜规划中心</h1>
            <div class="page-header__subtitle">
              以当前项目已采用的脚本结构为基线，生成、预览并保存可执行的 TikTok 分镜方案。
            </div>
          </div>
          <div class="page-header__actions">
            <Button
              v-if="isOutdated"
              variant="warning"
              :running="isBusy"
              data-action="sync-storyboard-script"
              @click="handleSync"
            >
              <template #leading><span class="material-symbols-outlined">sync</span></template>
              同步最新文案
            </Button>
            <Button
              variant="ai"
              :running="isGenerating"
              :disabled="generateDisabled"
              data-action="generate-storyboard"
              @click="handleGenerate"
            >
              <template #leading><span class="material-symbols-outlined">auto_awesome</span></template>
              AI 生成分镜
            </Button>
            <Button
              variant="primary"
              :disabled="saveDisabled"
              data-action="save-storyboard"
              @click="handleSave"
            >
              <template #leading><span class="material-symbols-outlined">save</span></template>
              保存分镜
            </Button>
          </div>
        </div>

        <div v-if="isOutdated && !isBusy" class="outdated-banner">
          <span class="material-symbols-outlined">warning</span>
          <p>
            检测到脚本文案已更新到 v{{ scriptRevision }}，当前分镜仍基于 v{{ basedOnScriptRevision }}。
            建议先同步文案，再继续编辑分镜内容。
          </p>
          <Button variant="secondary" size="sm" @click="handleSync">立即同步</Button>
        </div>
      </header>

      <div class="storyboard-workspace">
        <aside class="storyboard-panel storyboard-panel--script" data-storyboard-section="script-reference">
          <Card class="storyboard-card h-full">
            <div class="storyboard-card__header">
              <div>
                <h3>脚本结构对照</h3>
                <p class="storyboard-card__caption">展示当前已采用脚本结构，分镜生成与校对均以此为准。</p>
              </div>
              <Chip size="sm">v{{ scriptRevision || "-" }}</Chip>
            </div>
            <div class="storyboard-card__body scroll-area script-preview-pane" data-storyboard-script-preview>
              <div v-if="!hasScriptContent" class="empty-text">
                当前项目尚未采用脚本文案，请先到脚本与选题中心完成脚本确认。
              </div>
              <ScriptStructuredPreview
                v-else-if="scriptDocumentJson"
                :document-json="scriptDocumentJson"
              />
              <ScriptMarkdownPreview v-else :markdown="scriptMarkdownContent" />
            </div>
          </Card>
        </aside>

        <main class="storyboard-panel storyboard-panel--board">
          <Card
            class="storyboard-card h-full board-card"
            :class="{ 'is-generating': isGenerating }"
            data-storyboard-section="scene-board"
          >
            <div v-if="isGenerating" class="ai-flow-bar" />

            <div class="board-header">
              <div class="board-header__copy">
                <h3>分镜工作面</h3>
                <span class="board-meta">{{ boardMeta }}</span>
              </div>
              <div class="board-tags">
                <Chip v-if="currentRevisionLabel !== '-'" :variant="isOutdated ? 'warning' : 'default'">
                  基于文案 v{{ basedOnScriptRevision }}
                </Chip>
                <Chip v-if="currentModelLabel" variant="brand">{{ currentModelLabel }}</Chip>
                <Chip size="sm">{{ scenes.length }} 个分镜</Chip>
                <div class="editor-mode-switch" role="tablist" aria-label="分镜显示模式">
                  <button
                    type="button"
                    class="editor-mode-switch__button"
                    :class="{ 'is-active': editorMode === 'list' }"
                    data-storyboard-view="list"
                    @click="editorMode = 'list'"
                  >
                    列表视图
                  </button>
                  <button
                    type="button"
                    class="editor-mode-switch__button"
                    :class="{ 'is-active': editorMode === 'outline' }"
                    data-storyboard-view="outline"
                    @click="editorMode = 'outline'"
                  >
                    大纲视图
                  </button>
                  <button
                    type="button"
                    class="editor-mode-switch__button"
                    :class="{ 'is-active': editorMode === 'preview' }"
                    data-storyboard-view="preview"
                    @click="editorMode = 'preview'"
                  >
                    预览模式
                  </button>
                </div>
              </div>
            </div>

            <div class="board-body">
              <div v-if="pageState === 'loading'" class="board-empty">
                <span class="material-symbols-outlined spinning">progress_activity</span>
                <p>正在读取当前项目的分镜数据...</p>
              </div>
              <div v-else-if="pageState === 'error'" class="board-empty">
                <span class="material-symbols-outlined">error</span>
                <p>{{ pageStateDescription }}</p>
              </div>
              <div v-else-if="pageState === 'blocked'" class="board-empty">
                <span class="material-symbols-outlined">warning</span>
                <p>{{ pageStateDescription }}</p>
              </div>
              <div v-else-if="!hasScriptContent" class="board-empty">
                <span class="material-symbols-outlined">description</span>
                <p>
                  文案内容为空
                  <br />
                  <small>分镜规划依赖已采用脚本，请先完成脚本确认。</small>
                </p>
              </div>
              <div v-else-if="!hasStoryboardContent" class="board-empty">
                <span class="material-symbols-outlined">view_carousel</span>
                <p>
                  当前项目还没有生成分镜
                  <br />
                  <small>点击右上角“AI 生成分镜”，会基于脚本结构生成完整执行方案。</small>
                </p>
              </div>

              <div v-else class="storyboard-editor-content">
                <div class="storyboard-preview-pane scroll-area" data-storyboard-preview-mode>
                  <StoryboardStructuredPreview
                    v-if="storyboardDocumentJson"
                    :storyboard-json="storyboardDocumentJson"
                    :mode="editorMode"
                  />
                  <ScriptMarkdownPreview v-else :markdown="storyboardMarkdown" />
                </div>
              </div>
            </div>

            <div class="board-footer">
              <span>当前共 {{ storyboardLength }} 字，识别到 {{ scenes.length }} 个分镜。</span>
              <span>{{ currentRevisionDisplay }} · {{ latestJobLabel }}</span>
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
import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";
import ScriptMarkdownPreview from "@/pages/scripts/components/ScriptMarkdownPreview.vue";
import ScriptStructuredPreview from "@/pages/scripts/components/ScriptStructuredPreview.vue";
import StoryboardStructuredPreview from "@/pages/storyboards/components/StoryboardStructuredPreview.vue";
import { buildStoryboardMarkdown } from "@/pages/storyboards/storyboard-markdown";
import { useProjectStore } from "@/stores/project";
import { createRouteDetailContext, useShellUiStore } from "@/stores/shell-ui";
import { useScriptStudioStore } from "@/stores/script-studio";
import { useStoryboardStore } from "@/stores/storyboard";
import type { StoryboardScene } from "@/types/runtime";

type PageState = "loading" | "empty" | "ready" | "error" | "blocked";
type EditorMode = "list" | "outline" | "preview";

const projectStore = useProjectStore();
const scriptStudioStore = useScriptStudioStore();
const shellUiStore = useShellUiStore();
const storyboardStore = useStoryboardStore();

const scenes = ref<StoryboardScene[]>([]);
const storyboardSource = ref("");
const editorMode = ref<EditorMode>("list");
const selectedSceneId = ref<string | null>(null);

const currentProjectId = computed(() => projectStore.currentProject?.projectId ?? "");
const projectName = computed(() => projectStore.currentProject?.projectName ?? "未选择项目");
const basedOnScriptRevision = computed(() => storyboardStore.document?.basedOnScriptRevision ?? 0);
const scriptRevision = computed(() => scriptStudioStore.document?.currentVersion?.revision ?? 0);
const isOutdated = computed(() => {
  if (basedOnScriptRevision.value === 0 || scriptRevision.value === 0) return false;
  return basedOnScriptRevision.value < scriptRevision.value;
});

const recentJobs = computed(() => storyboardStore.document?.recentJobs ?? []);
const latestJob = computed(() => recentJobs.value[0] ?? null);
const currentVersion = computed(() => storyboardStore.document?.currentVersion ?? null);
const scriptDocumentJson = computed(() => scriptStudioStore.document?.currentVersion?.documentJson ?? null);
const storyboardDocumentJson = computed(() => currentVersion.value?.storyboardJson ?? null);
const hasScenes = computed(() => scenes.value.length > 0);
const hasScriptContent = computed(
  () => Boolean(scriptDocumentJson.value) || (scriptStudioStore.document?.currentVersion?.content ?? "").trim().length > 0
);
const scriptMarkdownContent = computed(() => scriptStudioStore.document?.currentVersion?.content ?? "");
const storyboardMarkdown = computed(() => storyboardSource.value);
const storyboardLength = computed(() =>
  storyboardDocumentJson.value
    ? JSON.stringify(storyboardDocumentJson.value).length
    : storyboardMarkdown.value.trim().length
);
const hasStoryboardContent = computed(() => Boolean(storyboardDocumentJson.value) || hasScenes.value || storyboardLength.value > 0);
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
    (storyboardStore.status === "loading" && !hasStoryboardContent.value) ||
    (scriptStudioStore.status === "loading" && !hasScriptContent.value)
  ) {
    return "loading";
  }
  if ((storyboardStore.status === "error" || scriptStudioStore.status === "error") && !hasStoryboardContent.value) {
    return "error";
  }
  if (!hasStoryboardContent.value) {
    return hasBlockedJob.value ? "blocked" : "empty";
  }
  return "ready";
});

const pageStateLabel = computed(() => {
  const map: Record<PageState, string> = {
    blocked: "能力阻断",
    empty: "空状态",
    error: "错误",
    loading: "加载中",
    ready: "已就绪"
  };
  return map[pageState.value];
});

const pageStateDescription = computed(() => {
  if (pageState.value === "loading") {
    return "正在通过 Runtime 拉取脚本文案、分镜版本和最近生成作业。";
  }
  if (pageState.value === "error") {
    return (
      storyboardStore.error?.message ??
      scriptStudioStore.error?.message ??
      "分镜加载失败，请检查 Runtime 状态。"
    );
  }
  if (pageState.value === "blocked") {
    return latestJob.value?.error ?? "最近一次分镜生成被阻断，请调整文案或稍后重试。";
  }
  if (pageState.value === "empty") {
    return hasScriptContent.value
      ? "当前项目已有脚本文案，可直接生成分镜。"
      : "分镜规划依赖脚本文案，请先完成脚本确认。";
  }
  return "当前页面展示真实分镜版本、作业状态与可继续编辑的镜头方案。";
});

const selectedScene = computed(
  () => scenes.value.find((scene) => scene.sceneId === selectedSceneId.value) ?? scenes.value[0] ?? null
);

const boardMeta = computed(() => {
  if (currentVersion.value) {
    return `基于文案 v${currentVersion.value.basedOnScriptRevision} 生成于 ${formatDateTime(currentVersion.value.createdAt)}`;
  }
  if (hasScriptContent.value) {
    return `当前脚本文案 v${scriptRevision.value} 已就绪，可直接生成分镜。`;
  }
  return "等待脚本文案同步后开始分镜规划。";
});

const currentRevisionLabel = computed(() => currentVersion.value?.revision ?? "-");
const currentRevisionDisplay = computed(() =>
  currentVersion.value ? `修订 ${currentVersion.value.revision}` : "尚未生成分镜版本"
);
const currentModelLabel = computed(() => currentVersion.value?.model ?? latestJob.value?.model ?? "");
const latestJobLabel = computed(() => {
  if (!latestJob.value) return "暂无作业";
  return `${jobStatusLabel(latestJob.value.status)} / ${latestJob.value.provider}`;
});

const generateDisabled = computed(() => isBusy.value || !hasScriptContent.value);
const saveDisabled = computed(() => isBusy.value || (!storyboardDocumentJson.value && storyboardLength.value === 0));

watch(
  currentProjectId,
  (projectId, previousProjectId) => {
    if (!projectId || projectId === previousProjectId) return;
    selectedSceneId.value = null;
    void storyboardStore.load(projectId);
    void scriptStudioStore.load(projectId);
  },
  { immediate: true }
);

watch(
  () => storyboardStore.document?.currentVersion?.scenes,
  (value) => {
    scenes.value = (value ?? []).map((scene) => normalizeScene(scene));
    selectedSceneId.value = scenes.value[0]?.sceneId ?? null;
    storyboardSource.value =
      storyboardStore.document?.currentVersion?.markdown || buildStoryboardMarkdown(scenes.value);
  },
  { immediate: true }
);

watch(
  [projectName, selectedScene, currentVersion, pageState, recentJobs, isOutdated],
  () => {
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
          { id: "revision", label: "分镜修订", value: currentRevisionDisplay.value },
          { id: "script", label: "文案版本", value: `v${scriptRevision.value || "-"}` },
          { id: "scenes", label: "分镜数量", value: String(scenes.value.length) }
        ],
        sections: [
          {
            id: "reference",
            title: "版本追踪",
            fields: [
              {
                id: "script",
                label: "文案基线",
                value: `v${basedOnScriptRevision.value}` + (isOutdated.value ? "（已过期）" : "")
              },
              {
                id: "scene",
                label: "当前分镜",
                value: selectedScene.value?.title ?? "未选择"
              }
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
  },
  { immediate: true }
);

onBeforeUnmount(() => {
  shellUiStore.clearDetailContext("contextual");
});

async function handleGenerate(): Promise<void> {
  await storyboardStore.generate();
}

async function handleSync(): Promise<void> {
  if (scenes.value.length > 0) {
    if (!confirm("同步最新文案会覆盖当前未保存的分镜修改，确认继续吗？")) return;
  }
  await storyboardStore.syncFromScript();
}

async function handleSave(): Promise<void> {
  const basedOnRevision = storyboardStore.document?.basedOnScriptRevision ?? scriptRevision.value;
  await storyboardStore.save(
    basedOnRevision,
    scenes.value.map((scene) => normalizeScene(scene)),
    storyboardDocumentJson.value ? null : storyboardMarkdown.value,
    storyboardDocumentJson.value
  );
}

function normalizeScene(scene: StoryboardScene): StoryboardScene {
  const visualContent = scene.visualContent ?? scene.summary ?? "";
  return {
    ...scene,
    action: scene.action ?? "",
    audio: scene.audio ?? "",
    cameraAngle: scene.cameraAngle ?? "",
    cameraMovement: scene.cameraMovement ?? "",
    shootingNote: scene.shootingNote ?? "",
    shotLabel: scene.shotLabel ?? scene.title ?? "",
    shotSize: scene.shotSize ?? "",
    subtitle: scene.subtitle ?? "",
    time: scene.time ?? "",
    title: scene.title || scene.shotLabel || "未命名镜头",
    transition: scene.transition ?? "",
    visualContent,
    visualPrompt: scene.visualPrompt ?? "",
    voiceover: scene.voiceover ?? ""
  };
}

function jobStatusLabel(status: string): string {
  if (status === "blocked") return "阻断";
  if (status === "failed") return "失败";
  if (status === "running") return "运行中";
  if (status === "queued") return "排队中";
  if (status === "succeeded") return "已完成";
  return status;
}

function formatDateTime(value: string): string {
  if (!value) return "未知时间";
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    hour12: false,
    minute: "2-digit",
    month: "numeric",
    day: "numeric"
  }).format(new Date(value));
}
</script>

<style scoped src="./StoryboardPlanningCenterPage.css"></style>
