<template>
  <ProjectContextGuard>
    <section class="storyboard-planning-center">
      <header class="storyboard-planning-center__header">
        <div class="storyboard-planning-center__headline">
          <p class="storyboard-planning-center__eyebrow">创作策划 / Storyboard</p>
          <h1>分镜规划中心</h1>
          <p class="storyboard-planning-center__summary">
            把脚本结构转成真实分镜版本，当前生成状态、脚本引用和镜头内容都直接回到项目主链。
          </p>
        </div>
        <div class="storyboard-planning-center__meta">
          <span class="storyboard-planning-center__chip storyboard-planning-center__chip--project">
            {{ projectName }}
          </span>
          <span class="storyboard-planning-center__chip">
            脚本引用 v{{ basedOnScriptRevision }}
          </span>
          <span class="storyboard-planning-center__chip" :data-tone="pageState">
            {{ pageStateLabel }}
          </span>
        </div>
      </header>

      <section class="storyboard-planning-center__toolbar">
        <div class="storyboard-planning-center__toolbar-copy">
          <strong>分镜工作面</strong>
          <p>生成、保存与版本摘要继续通过 `storyboard` store 走真实 Runtime 契约。</p>
        </div>
        <div class="storyboard-planning-center__toolbar-actions">
          <span class="storyboard-planning-center__view-switch">
            <button class="storyboard-planning-center__view-button storyboard-planning-center__view-button--active" type="button">
              卡片瀑布
            </button>
            <button class="storyboard-planning-center__view-button" type="button" disabled>
              节奏视图
            </button>
            <button class="storyboard-planning-center__view-button" type="button" disabled>
              结构对比
            </button>
          </span>
          <button
            class="storyboard-planning-center__button storyboard-planning-center__button--ai"
            type="button"
            data-action="generate-storyboard"
            :disabled="generateDisabled"
            @click="handleGenerate"
          >
            <span class="material-symbols-outlined">auto_awesome</span>
            AI 生成分镜
          </button>
          <button
            class="storyboard-planning-center__button storyboard-planning-center__button--primary"
            type="button"
            data-action="save-storyboard"
            :disabled="saveDisabled"
            @click="handleSave"
          >
            <span class="material-symbols-outlined">save</span>
            保存分镜
          </button>
        </div>
      </section>

      <section
        class="storyboard-planning-center__state-banner"
        :class="`storyboard-planning-center__state-banner--${pageState}`"
      >
        <span class="material-symbols-outlined">{{ pageStateIcon }}</span>
        <div>
          <strong>{{ pageStateTitle }}</strong>
          <p>{{ pageStateDescription }}</p>
        </div>
      </section>

      <div class="storyboard-planning-center__workspace">
        <aside class="storyboard-planning-center__panel storyboard-planning-center__panel--script" data-storyboard-section="script-nav">
          <div class="storyboard-planning-center__panel-heading">
            <div>
              <h2>脚本段落导航</h2>
              <p>左侧只展示真实脚本内容拆出的段落锚点。</p>
            </div>
            <span>{{ scriptSegments.length }} 段</span>
          </div>

          <div v-if="scriptSegments.length === 0" class="storyboard-planning-center__empty-inline">
            脚本中心尚无可引用正文，先完成脚本生成或保存。
          </div>
          <div v-else class="storyboard-planning-center__segment-list">
            <button
              v-for="segment in scriptSegments"
              :key="segment.id"
              class="storyboard-planning-center__segment"
              :class="{ 'storyboard-planning-center__segment--active': selectedSegmentId === segment.id }"
              type="button"
              @click="selectedSegmentId = segment.id"
            >
              <strong>{{ segment.title }}</strong>
              <p>{{ segment.excerpt }}</p>
            </button>
          </div>
        </aside>

        <main class="storyboard-planning-center__panel storyboard-planning-center__panel--board" data-storyboard-section="scene-board">
          <div class="storyboard-planning-center__panel-heading">
            <div>
              <h2>镜头规划板</h2>
              <p>{{ boardMeta }}</p>
            </div>
            <span class="storyboard-planning-center__scene-count">
              {{ scenes.length }} 个镜头
            </span>
          </div>

          <div v-if="pageState === 'loading'" class="storyboard-planning-center__loading">
            <span class="material-symbols-outlined">progress_activity</span>
            正在同步分镜版本与脚本引用。
          </div>
          <div v-else-if="!hasScriptContent" class="storyboard-planning-center__empty">
            <span class="material-symbols-outlined">description</span>
            <div>
              <strong>脚本尚未准备好</strong>
              <p>分镜规划依赖真实脚本内容，当前不会展示伪造场景卡。</p>
            </div>
          </div>
          <div v-else-if="scenes.length === 0" class="storyboard-planning-center__empty">
            <span class="material-symbols-outlined">view_carousel</span>
            <div>
              <strong>当前项目还没有分镜版本</strong>
              <p>点击“AI 生成分镜”后，Runtime 返回的真实场景会直接落在这里。</p>
            </div>
          </div>
          <div v-else class="storyboard-planning-center__scene-grid">
            <article
              v-for="(scene, index) in scenes"
              :key="scene.sceneId"
              class="storyboard-planning-center__scene-card"
              :class="{ 'storyboard-planning-center__scene-card--active': selectedSceneId === scene.sceneId }"
              data-scene-card
              @click="selectedSceneId = scene.sceneId"
            >
              <div class="storyboard-planning-center__scene-header">
                <div>
                  <small>镜头 {{ index + 1 }}</small>
                  <strong>{{ linkedSegmentTitle(index) }}</strong>
                </div>
                <span>v{{ currentRevisionLabel }}</span>
              </div>

              <label class="storyboard-planning-center__field">
                <span>标题</span>
                <input v-model="scene.title" />
              </label>

              <label class="storyboard-planning-center__field">
                <span>摘要</span>
                <textarea v-model="scene.summary" />
              </label>

              <label class="storyboard-planning-center__field">
                <span>视觉提示</span>
                <textarea v-model="scene.visualPrompt" />
              </label>

              <footer class="storyboard-planning-center__scene-footer">
                <span>{{ versionSourceLabel }}</span>
                <span>{{ currentVersionTimestamp }}</span>
              </footer>
            </article>
          </div>
        </main>

        <aside class="storyboard-planning-center__rail">
          <section class="storyboard-planning-center__panel" data-storyboard-section="version-summary">
            <div class="storyboard-planning-center__panel-heading">
              <div>
                <h2>版本与生成状态</h2>
                <p>显示当前版本、历史修订和最近 AI 作业，不补伪进度。</p>
              </div>
            </div>

            <div class="storyboard-planning-center__version-card">
              <small>当前版本</small>
              <strong>{{ currentRevisionDisplay }}</strong>
              <p>{{ currentVersionDescription }}</p>
            </div>

            <div v-if="versions.length === 0" class="storyboard-planning-center__empty-inline">
              还没有分镜版本。
            </div>
            <ul v-else class="storyboard-planning-center__version-list">
              <li v-for="version in versions" :key="version.revision">
                <strong>修订 {{ version.revision }}</strong>
                <p>{{ version.source }} · {{ version.provider ?? "手动" }}</p>
                <small>{{ formatDateTime(version.createdAt) }}</small>
              </li>
            </ul>

            <div class="storyboard-planning-center__job-panel">
              <small>最近作业</small>
              <strong>{{ latestJobTitle }}</strong>
              <p>{{ latestJobDescription }}</p>
            </div>
          </section>
        </aside>
      </div>
    </section>
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
const basedOnScriptRevision = computed(() => storyboardStore.document?.basedOnScriptRevision ?? "-");
const versions = computed(() => storyboardStore.document?.versions ?? []);
const recentJobs = computed(() => storyboardStore.document?.recentJobs ?? []);
const latestJob = computed(() => recentJobs.value[0] ?? null);
const currentVersion = computed(() => storyboardStore.document?.currentVersion ?? null);
const hasScenes = computed(() => scenes.value.length > 0);
const hasScriptContent = computed(
  () => (scriptStudioStore.document?.currentVersion?.content ?? "").trim().length > 0
);
const hasBlockedJob = computed(() => recentJobs.value.some((job) => job.status === "blocked"));
const isBusy = computed(
  () =>
    storyboardStore.status === "loading" ||
    storyboardStore.status === "saving" ||
    storyboardStore.status === "generating"
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
  const map: Record<PageState, string> = {
    blocked: "能力阻断",
    empty: "空态",
    error: "错误",
    loading: "加载中",
    ready: "已就绪"
  };
  return map[pageState.value];
});
const pageStateIcon = computed(() => {
  const map: Record<PageState, string> = {
    blocked: "lock",
    empty: "view_carousel",
    error: "error",
    loading: "progress_activity",
    ready: "task_alt"
  };
  return map[pageState.value];
});
const pageStateTitle = computed(() => {
  if (pageState.value === "loading") return "正在同步分镜规划上下文";
  if (pageState.value === "error") return "分镜请求失败";
  if (pageState.value === "blocked") return "最近一次分镜作业被阻断";
  if (pageState.value === "empty") return "还没有真实分镜版本";
  return "分镜工作面已就绪";
});
const pageStateDescription = computed(() => {
  if (pageState.value === "loading") {
    return "页面正在同时读取脚本引用和分镜版本，不生成伪场景卡。";
  }
  if (pageState.value === "error") {
    return errorSummary.value;
  }
  if (pageState.value === "blocked") {
    return latestJob.value?.error ?? "最近一次 AI 分镜作业被阻断，当前仍可继续手动编辑已有版本。";
  }
  if (pageState.value === "empty") {
    return hasScriptContent.value
      ? "脚本已就绪，但当前项目还没有分镜版本。"
      : "先完成真实脚本，再进入分镜生成。";
  }
  return "当前页面展示真实脚本引用、场景版本和最近生成状态。";
});
const errorSummary = computed(() => {
  const storyboardError = storyboardStore.error?.message;
  const scriptError = scriptStudioStore.error?.message;
  return storyboardError ?? scriptError ?? "分镜请求失败，请稍后重试。";
});
const scriptSegments = computed(() =>
  parseScriptSegments(scriptStudioStore.document?.currentVersion?.content ?? "")
);
const selectedScene = computed(() =>
  scenes.value.find((scene) => scene.sceneId === selectedSceneId.value) ?? scenes.value[0] ?? null
);
const boardMeta = computed(() => {
  if (currentVersion.value) {
    return `基于脚本修订 v${currentVersion.value.basedOnScriptRevision} 生成，当前版本写入于 ${formatDateTime(currentVersion.value.createdAt)}`;
  }

  if (hasScriptContent.value) {
    return `脚本修订 v${basedOnScriptRevision.value} 已就绪，等待生成首个分镜版本。`;
  }

  return "等待脚本内容进入分镜规划链路。";
});
const currentRevisionLabel = computed(() => currentVersion.value?.revision ?? "-");
const currentRevisionDisplay = computed(() =>
  currentVersion.value ? `修订 ${currentVersion.value.revision}` : "尚无分镜修订"
);
const currentVersionDescription = computed(() => {
  if (!currentVersion.value) {
    return "当前项目还没有分镜版本。";
  }

  return `${currentVersion.value.source} · ${currentVersion.value.provider ?? "手动"} · ${currentVersion.value.model ?? "未标注模型"}`;
});
const currentVersionTimestamp = computed(() =>
  currentVersion.value ? formatDateTime(currentVersion.value.createdAt) : "尚未生成"
);
const versionSourceLabel = computed(() => currentVersion.value?.source ?? "等待版本");
const latestJobTitle = computed(() => {
  if (!latestJob.value) {
    return "暂无真实分镜作业";
  }

  return `${latestJob.value.provider} · ${latestJob.value.model}`;
});
const latestJobDescription = computed(() => {
  if (!latestJob.value) {
    return "后续 AI 生成、阻断或失败信息都会写回这里。";
  }

  return `${jobStatusLabel(latestJob.value.status)} · ${formatDateTime(latestJob.value.createdAt)}`;
});
const generateDisabled = computed(() => isBusy.value || !hasScriptContent.value);
const saveDisabled = computed(() => isBusy.value || scenes.value.length === 0);

watch(
  currentProjectId,
  (projectId, previousProjectId) => {
    if (!projectId || projectId === previousProjectId) {
      return;
    }

    selectedSceneId.value = null;
    selectedSegmentId.value = null;
    void storyboardStore.load(projectId);
    void scriptStudioStore.load(projectId);
  },
  { immediate: true }
);

watch(
  () => storyboardStore.document?.currentVersion?.scenes,
  (value) => {
    scenes.value = (value ?? []).map((scene) => ({ ...scene }));
    selectedSceneId.value = scenes.value[0]?.sceneId ?? null;
  },
  { immediate: true }
);

watch(
  scriptSegments,
  (value) => {
    selectedSegmentId.value = value[0]?.id ?? null;
  },
  { immediate: true }
);

watch(
  [projectName, selectedScene, currentVersion, pageState, latestJob, scriptSegments],
  () => {
    shellUiStore.setDetailContext(
      createRouteDetailContext("contextual", {
        icon: "view_timeline",
        eyebrow: "分镜规划中心",
        title: projectName.value,
        description: pageStateDescription.value,
        badge: {
          label: pageStateLabel.value,
          tone: pageState.value === "error" ? "danger" : pageState.value === "blocked" ? "warning" : "brand"
        },
        metrics: [
          { id: "revision", label: "当前修订", value: currentRevisionDisplay.value },
          { id: "segments", label: "脚本段落", value: String(scriptSegments.value.length) },
          { id: "scenes", label: "镜头数", value: String(scenes.value.length) }
        ],
        sections: [
          {
            id: "reference",
            title: "脚本引用",
            fields: [
              { id: "script", label: "脚本修订", value: `v${basedOnScriptRevision.value}` },
              { id: "scene", label: "当前镜头", value: selectedScene.value?.title ?? "未选择" }
            ]
          },
          {
            id: "jobs",
            title: "最近作业",
            emptyLabel: "当前没有真实 AI 分镜作业。",
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

async function handleSave(): Promise<void> {
  const basedOnRevision =
    currentVersion.value?.basedOnScriptRevision ??
    storyboardStore.document?.basedOnScriptRevision ??
    1;
  await storyboardStore.save(basedOnRevision, scenes.value);
}

function linkedSegmentTitle(index: number): string {
  return scriptSegments.value[index]?.title ?? `脚本段落 ${index + 1}`;
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
  if (!value) {
    return "未知时间";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    hour12: false,
    minute: "2-digit",
    month: "numeric",
    day: "numeric"
  }).format(new Date(value));
}

function parseScriptSegments(value: string): Array<{ excerpt: string; id: string; title: string }> {
  return value
    .split(/\n\s*\n/)
    .map((segment) => segment.trim())
    .filter(Boolean)
    .map((segment, index) => {
      const lines = segment
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);
      const rawTitle = lines[0] ?? `段落 ${index + 1}`;
      return {
        excerpt: lines.slice(1).join(" ").slice(0, 88) || "等待补充脚本段落。",
        id: `segment-${index + 1}`,
        title: rawTitle.replace(/^#+\s*/, "")
      };
    });
}
</script>

<style scoped>
.storyboard-planning-center {
  display: grid;
  gap: 20px;
}

.storyboard-planning-center__header,
.storyboard-planning-center__toolbar {
  align-items: flex-start;
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.storyboard-planning-center__headline {
  display: grid;
  gap: 8px;
}

.storyboard-planning-center__eyebrow {
  color: var(--text-tertiary);
  font-size: 12px;
  letter-spacing: 0.12em;
  margin: 0;
  text-transform: uppercase;
}

.storyboard-planning-center__summary,
.storyboard-planning-center__panel-heading p,
.storyboard-planning-center__toolbar-copy p,
.storyboard-planning-center__segment p,
.storyboard-planning-center__state-banner p,
.storyboard-planning-center__version-card p,
.storyboard-planning-center__empty-inline,
.storyboard-planning-center__empty p {
  color: var(--text-secondary);
  margin: 0;
}

.storyboard-planning-center__meta,
.storyboard-planning-center__toolbar-actions,
.storyboard-planning-center__view-switch,
.storyboard-planning-center__scene-footer {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.storyboard-planning-center__chip,
.storyboard-planning-center__scene-count {
  background: color-mix(in srgb, var(--surface-tertiary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 999px;
  color: var(--text-secondary);
  font-size: 12px;
  padding: 6px 12px;
}

.storyboard-planning-center__chip--project {
  color: var(--text-primary);
}

.storyboard-planning-center__chip[data-tone="ready"] {
  border-color: color-mix(in srgb, var(--color-success) 35%, var(--border-default));
  color: var(--color-success);
}

.storyboard-planning-center__chip[data-tone="blocked"] {
  border-color: color-mix(in srgb, var(--color-warning) 35%, var(--border-default));
  color: var(--color-warning);
}

.storyboard-planning-center__chip[data-tone="error"] {
  border-color: color-mix(in srgb, var(--color-danger) 35%, var(--border-default));
  color: var(--color-danger);
}

.storyboard-planning-center__toolbar,
.storyboard-planning-center__state-banner,
.storyboard-planning-center__panel {
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 20px;
  box-shadow: var(--shadow-sm);
}

.storyboard-planning-center__toolbar {
  padding: 18px 20px;
}

.storyboard-planning-center__toolbar-copy {
  display: grid;
  gap: 6px;
}

.storyboard-planning-center__view-button,
.storyboard-planning-center__button {
  border: 1px solid transparent;
  border-radius: 8px;
  height: 38px;
  padding: 0 14px;
}

.storyboard-planning-center__view-button {
  background: transparent;
  border-color: var(--border-default);
  color: var(--text-secondary);
}

.storyboard-planning-center__view-button--active {
  color: var(--text-primary);
}

.storyboard-planning-center__button {
  align-items: center;
  display: inline-flex;
  gap: 8px;
}

.storyboard-planning-center__button:disabled,
.storyboard-planning-center__view-button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.storyboard-planning-center__button--primary {
  background: var(--brand-primary);
  color: var(--text-inverse, #041314);
}

.storyboard-planning-center__button--ai {
  background: var(--gradient-ai-primary);
  color: #fff;
}

.storyboard-planning-center__state-banner {
  align-items: center;
  display: flex;
  gap: 14px;
  padding: 14px 18px;
}

.storyboard-planning-center__state-banner--error {
  border-color: color-mix(in srgb, var(--color-danger) 35%, var(--border-default));
}

.storyboard-planning-center__state-banner--blocked {
  border-color: color-mix(in srgb, var(--color-warning) 35%, var(--border-default));
}

.storyboard-planning-center__workspace {
  display: grid;
  gap: 18px;
  grid-template-columns: minmax(260px, 300px) minmax(0, 1fr) minmax(280px, 320px);
}

.storyboard-planning-center__panel,
.storyboard-planning-center__rail {
  display: grid;
  gap: 16px;
}

.storyboard-planning-center__panel {
  align-content: start;
  padding: 18px;
}

.storyboard-planning-center__panel-heading,
.storyboard-planning-center__scene-header {
  align-items: center;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.storyboard-planning-center__segment-list,
.storyboard-planning-center__version-list {
  display: grid;
  gap: 10px;
}

.storyboard-planning-center__segment,
.storyboard-planning-center__scene-card,
.storyboard-planning-center__version-list li,
.storyboard-planning-center__version-card,
.storyboard-planning-center__job-panel {
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 16px;
  padding: 14px;
}

.storyboard-planning-center__segment {
  display: grid;
  gap: 6px;
  text-align: left;
}

.storyboard-planning-center__segment--active {
  border-color: color-mix(in srgb, var(--brand-primary) 32%, var(--border-default));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--brand-primary) 28%, transparent);
}

.storyboard-planning-center__loading,
.storyboard-planning-center__empty {
  align-items: center;
  border: 1px dashed var(--border-default);
  border-radius: 18px;
  color: var(--text-secondary);
  display: flex;
  gap: 14px;
  justify-content: center;
  min-height: 320px;
  padding: 24px;
  text-align: center;
}

.storyboard-planning-center__scene-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.storyboard-planning-center__scene-card {
  cursor: pointer;
  display: grid;
  gap: 12px;
}

.storyboard-planning-center__scene-card--active {
  border-color: color-mix(in srgb, var(--brand-primary) 32%, var(--border-default));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--brand-primary) 28%, transparent);
}

.storyboard-planning-center__scene-header small,
.storyboard-planning-center__version-card small,
.storyboard-planning-center__job-panel small,
.storyboard-planning-center__scene-footer {
  color: var(--text-tertiary);
}

.storyboard-planning-center__field {
  display: grid;
  gap: 8px;
}

.storyboard-planning-center__field span {
  color: var(--text-secondary);
  font-size: 12px;
}

.storyboard-planning-center__field input,
.storyboard-planning-center__field textarea {
  background: color-mix(in srgb, var(--surface-secondary) 82%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  color: var(--text-primary);
  padding: 12px 14px;
}

.storyboard-planning-center__field textarea {
  min-height: 96px;
  resize: vertical;
}

.storyboard-planning-center__version-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.storyboard-planning-center__version-list li {
  display: grid;
  gap: 4px;
}

.storyboard-planning-center__version-list p,
.storyboard-planning-center__version-list small {
  color: var(--text-secondary);
  margin: 0;
}

.storyboard-planning-center__job-panel {
  display: grid;
  gap: 6px;
}

@media (max-width: 1280px) {
  .storyboard-planning-center__workspace {
    grid-template-columns: minmax(240px, 280px) minmax(0, 1fr);
  }

  .storyboard-planning-center__rail {
    grid-column: 1 / -1;
  }
}

@media (max-width: 960px) {
  .storyboard-planning-center__header,
  .storyboard-planning-center__toolbar,
  .storyboard-planning-center__panel-heading,
  .storyboard-planning-center__scene-header {
    align-items: stretch;
    flex-direction: column;
  }

  .storyboard-planning-center__workspace {
    grid-template-columns: 1fr;
  }
}
</style>
