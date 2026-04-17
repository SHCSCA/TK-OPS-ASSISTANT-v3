<template>
  <ProjectContextGuard>
    <section class="script-topic-center">
      <header class="script-topic-center__header">
        <div class="script-topic-center__headline">
          <p class="script-topic-center__eyebrow">创作策划 / Script Studio</p>
          <h1>脚本与选题中心</h1>
          <p class="script-topic-center__summary">
            主题、脚本、版本和 AI 改写继续挂在同一个项目链路上，不再拆成零散表单。
          </p>
        </div>
        <div class="script-topic-center__meta">
          <span class="script-topic-center__chip script-topic-center__chip--project">
            {{ projectName }}
          </span>
          <span class="script-topic-center__chip">
            {{ revisionLabel }}
          </span>
          <span class="script-topic-center__chip" :data-tone="pageState">
            {{ pageStateLabel }}
          </span>
        </div>
      </header>

      <section class="script-topic-center__control-bar">
        <div class="script-topic-center__control-copy">
          <strong>策划工作台</strong>
          <p>
            当前版本 {{ revisionLabel }}，脚本生成、改写和保存都通过 `script-studio` store 回到项目主链。
          </p>
        </div>
        <div class="script-topic-center__control-actions">
          <button
            class="script-topic-center__button script-topic-center__button--ai"
            type="button"
            data-action="generate-script"
            :disabled="generateDisabled"
            @click="handleGenerate"
          >
            <span class="material-symbols-outlined">auto_awesome</span>
            AI 生成脚本
          </button>
          <button
            class="script-topic-center__button script-topic-center__button--ghost"
            type="button"
            data-action="rewrite-script"
            :disabled="rewriteDisabled"
            @click="handleRewrite"
          >
            <span class="material-symbols-outlined">ink_eraser</span>
            改写当前版本
          </button>
          <button
            class="script-topic-center__button script-topic-center__button--primary"
            type="button"
            data-action="save-script"
            :disabled="saveDisabled"
            @click="handleSave"
          >
            <span class="material-symbols-outlined">save</span>
            保存脚本
          </button>
        </div>
      </section>

      <section
        class="script-topic-center__state-banner"
        :class="`script-topic-center__state-banner--${pageState}`"
      >
        <span class="material-symbols-outlined">{{ pageStateIcon }}</span>
        <div>
          <strong>{{ pageStateTitle }}</strong>
          <p>{{ pageStateDescription }}</p>
        </div>
      </section>

      <div class="script-topic-center__workspace">
        <aside class="script-topic-center__panel script-topic-center__panel--prompt" data-script-section="prompt-panel">
          <div class="script-topic-center__panel-heading">
            <div>
              <h2>策划输入台</h2>
              <p>保留真实主题和改写指令入口，不在页面内拼接业务规则。</p>
            </div>
            <span class="script-topic-center__mini-status">{{ disabledReason }}</span>
          </div>

          <label class="script-topic-center__field">
            <span>主题</span>
            <input v-model="topic" data-field="script.topic" :disabled="isBusy" />
          </label>

          <label class="script-topic-center__field">
            <span>改写要求</span>
            <textarea
              v-model="instructions"
              data-field="script.instructions"
              :disabled="isBusy"
            />
          </label>

          <section class="script-topic-center__brief">
            <div class="script-topic-center__brief-card">
              <small>项目链路</small>
              <strong>{{ projectChainLabel }}</strong>
              <p>脚本会继续回流到 Project 与 Script Studio。</p>
            </div>
            <div class="script-topic-center__brief-card">
              <small>当前主标题</small>
              <strong>{{ titleSeed }}</strong>
              <p>来自真实脚本正文第一段，不生成伪变体。</p>
            </div>
          </section>

          <section class="script-topic-center__outline">
            <div class="script-topic-center__subheading">
              <strong>结构锚点</strong>
              <span>{{ outlineSegments.length }} 段</span>
            </div>
            <ol v-if="outlineSegments.length > 0" class="script-topic-center__outline-list">
              <li v-for="segment in outlineSegments" :key="segment.id">
                <strong>{{ segment.title }}</strong>
                <p>{{ segment.excerpt }}</p>
              </li>
            </ol>
            <div v-else class="script-topic-center__empty-inline">
              还没有正文结构，先生成脚本或从现有版本继续编辑。
            </div>
          </section>
        </aside>

        <main class="script-topic-center__panel script-topic-center__panel--editor" data-script-section="editor">
          <div class="script-topic-center__panel-heading">
            <div>
              <h2>脚本工作面</h2>
              <p>
                {{ displayedVersionMeta }}
              </p>
            </div>
            <div class="script-topic-center__editor-meta">
              <span>{{ currentSourceLabel }}</span>
              <span>{{ currentModelLabel }}</span>
            </div>
          </div>

          <div v-if="pageState === 'loading'" class="script-topic-center__loading">
            <span class="material-symbols-outlined">progress_activity</span>
            正在通过 Runtime 拉取当前项目脚本。
          </div>
          <div v-else-if="pageState === 'empty'" class="script-topic-center__empty">
            <span class="material-symbols-outlined">description</span>
            <div>
              <strong>当前项目还没有脚本版本</strong>
              <p>先填写主题后生成脚本，或等待 Script Studio 写入首个版本。</p>
            </div>
          </div>
          <div v-else class="script-topic-center__editor-shell">
            <textarea
              v-model="content"
              class="script-topic-center__editor"
              data-field="script.content"
              :disabled="isBusy || pageState === 'empty'"
            />
            <section class="script-topic-center__editor-foot">
              <div>
                <strong>正文摘要</strong>
                <p>当前共 {{ contentLength }} 字，按真实段落拆成 {{ outlineSegments.length }} 个策划锚点。</p>
              </div>
              <span>{{ updatedAtLabel }}</span>
            </section>
          </div>
        </main>

        <aside class="script-topic-center__rail">
          <section class="script-topic-center__panel" data-script-section="versions">
            <div class="script-topic-center__panel-heading">
              <div>
                <h2>版本轨迹</h2>
                <p>直接展示真实修订，不在 UI 中制造演示版本。</p>
              </div>
              <span>{{ versions.length }} 条</span>
            </div>
            <div v-if="versions.length === 0" class="script-topic-center__empty-inline">
              当前项目还没有脚本版本。
            </div>
            <div v-else class="script-topic-center__version-list">
              <button
                v-for="version in versions"
                :key="version.revision"
                class="script-topic-center__version"
                :class="{ 'script-topic-center__version--active': selectedRevision === version.revision }"
                data-script-version-item
                type="button"
                @click="selectedRevision = version.revision"
              >
                <div>
                  <strong>修订 {{ version.revision }}</strong>
                  <p>{{ version.source }} · {{ version.provider ?? "手动" }}</p>
                </div>
                <small>{{ formatDateTime(version.createdAt) }}</small>
              </button>
            </div>
          </section>

          <section class="script-topic-center__panel" data-script-section="title-variants">
            <div class="script-topic-center__panel-heading">
              <div>
                <h2>标题方向与 AI 作业</h2>
                <p>仅显示真实作业和当前主标题，不生成伪造标题列表。</p>
              </div>
            </div>

            <div class="script-topic-center__title-card">
              <small>当前主标题</small>
              <strong>{{ titleSeed }}</strong>
            </div>

            <div v-if="recentJobs.length === 0" class="script-topic-center__empty-inline">
              当前还没有真实标题变体结果，后续会跟随脚本生成一起写入版本记录。
            </div>
            <ul v-else class="script-topic-center__job-list">
              <li v-for="job in recentJobs" :key="job.id" class="script-topic-center__job">
                <div>
                  <strong>{{ capabilityLabel(job.capabilityId) }}</strong>
                  <p>{{ job.provider }} · {{ job.model }}</p>
                </div>
                <span :data-job-state="job.status">{{ jobStatusLabel(job.status) }}</span>
              </li>
            </ul>
          </section>
        </aside>
      </div>
    </section>
  </ProjectContextGuard>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onBeforeUnmount, ref, watch } from "vue";

import ProjectContextGuard from "@/components/common/ProjectContextGuard.vue";
import { createRouteDetailContext, useShellUiStore } from "@/stores/shell-ui";
import { useProjectStore } from "@/stores/project";
import { useScriptStudioStore } from "@/stores/script-studio";
import type { ScriptVersion } from "@/types/runtime";

type PageState = "loading" | "empty" | "ready" | "error" | "blocked";

const projectStore = useProjectStore();
const scriptStore = useScriptStudioStore();
const shellUiStore = useShellUiStore();
const { document } = storeToRefs(scriptStore);

const content = ref("");
const topic = ref("");
const instructions = ref("");
const selectedRevision = ref<number | null>(null);

const currentProjectId = computed(() => projectStore.currentProject?.projectId ?? "");
const projectName = computed(() => projectStore.currentProject?.projectName ?? "未选择项目");
const versions = computed(() => document.value?.versions ?? []);
const recentJobs = computed(() => document.value?.recentJobs ?? []);
const latestJob = computed(() => recentJobs.value[0] ?? null);
const currentVersion = computed(() => document.value?.currentVersion ?? null);
const displayedVersion = computed<ScriptVersion | null>(() => {
  if (selectedRevision.value === null) {
    return currentVersion.value;
  }

  return versions.value.find((version) => version.revision === selectedRevision.value) ?? currentVersion.value;
});
const hasDocument = computed(() => currentVersion.value !== null || versions.value.length > 0);
const isBusy = computed(
  () => scriptStore.status === "loading" || scriptStore.status === "saving" || scriptStore.status === "generating"
);
const hasBlockedJob = computed(() => recentJobs.value.some((job) => job.status === "blocked"));
const pageState = computed<PageState>(() => {
  if (scriptStore.status === "loading" && !hasDocument.value) return "loading";
  if (scriptStore.status === "error") return "error";
  if (!hasDocument.value) return "empty";
  if (hasBlockedJob.value) return "blocked";
  return "ready";
});
const revisionLabel = computed(() =>
  currentVersion.value ? `修订 ${currentVersion.value.revision}` : "尚无修订"
);
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
    empty: "notes",
    error: "error",
    loading: "progress_activity",
    ready: "task_alt"
  };
  return map[pageState.value];
});
const pageStateTitle = computed(() => {
  if (pageState.value === "loading") return "正在同步 Script Studio";
  if (pageState.value === "empty") return "脚本链路仍为空";
  if (pageState.value === "error") return "脚本请求失败";
  if (pageState.value === "blocked") return "AI 作业存在阻断";
  return "脚本工作面已就绪";
});
const pageStateDescription = computed(() => {
  if (pageState.value === "loading") {
    return "当前页面正在通过真实 Runtime 读取脚本版本和 AI 作业。";
  }
  if (pageState.value === "empty") {
    return "还没有脚本版本时，不展示伪造策划结果，只保留真实生成入口。";
  }
  if (pageState.value === "error") {
    return errorSummary.value;
  }
  if (pageState.value === "blocked") {
    return latestJob.value?.error ?? "最近一次 AI 作业被阻断，当前仍可继续手动编辑与保存。";
  }
  return "当前页面使用真实项目、脚本版本和 AI 作业状态构成策划工作台。";
});
const errorSummary = computed(() => {
  if (!scriptStore.error) {
    return "脚本请求失败，请稍后重试。";
  }

  return scriptStore.error.requestId
    ? `${scriptStore.error.message}（${scriptStore.error.requestId}）`
    : scriptStore.error.message;
});
const disabledReason = computed(() => {
  if (!currentProjectId.value) return "等待项目上下文";
  if (scriptStore.status === "loading") return "正在加载";
  if (scriptStore.status === "saving") return "正在保存";
  if (scriptStore.status === "generating") return "AI 正在处理中";
  return "动作可用";
});
const generateDisabled = computed(() => isBusy.value || topic.value.trim().length === 0);
const rewriteDisabled = computed(() => isBusy.value || instructions.value.trim().length === 0 || !hasDocument.value);
const saveDisabled = computed(() => isBusy.value || content.value.trim().length === 0 || pageState.value === "empty");
const contentLength = computed(() => content.value.trim().length);
const outlineSegments = computed(() => parseScriptSegments(content.value));
const titleSeed = computed(() => outlineSegments.value[0]?.title ?? "等待真实脚本标题");
const projectChainLabel = computed(() => `${projectName.value} / Script Studio / Project`);
const displayedVersionMeta = computed(() => {
  if (!displayedVersion.value) {
    return "暂无脚本版本，等待当前项目写入正文。";
  }

  return `当前查看修订 ${displayedVersion.value.revision} · ${formatDateTime(displayedVersion.value.createdAt)}`;
});
const currentSourceLabel = computed(() => displayedVersion.value?.source ?? "无来源");
const currentModelLabel = computed(() => displayedVersion.value?.model ?? "手动编辑");
const updatedAtLabel = computed(() =>
  displayedVersion.value ? `写入时间 ${formatDateTime(displayedVersion.value.createdAt)}` : "尚未写入"
);

watch(
  currentProjectId,
  (projectId, previousProjectId) => {
    if (!projectId || projectId === previousProjectId) {
      return;
    }
    topic.value = "";
    instructions.value = "";
    selectedRevision.value = null;
    void scriptStore.load(projectId);
  },
  { immediate: true }
);

watch(
  currentVersion,
  (value) => {
    selectedRevision.value = value?.revision ?? null;
  },
  { immediate: true }
);

watch(
  displayedVersion,
  (value) => {
    content.value = value?.content ?? "";
  },
  { immediate: true }
);

watch(
  [projectName, revisionLabel, pageState, latestJob, currentVersion, titleSeed],
  () => {
    shellUiStore.setDetailContext(
      createRouteDetailContext("contextual", {
        icon: "description",
        eyebrow: "脚本与选题中心",
        title: projectName.value,
        description: pageStateDescription.value,
        badge: {
          label: pageStateLabel.value,
          tone: pageState.value === "error" ? "danger" : pageState.value === "blocked" ? "warning" : "brand"
        },
        metrics: [
          { id: "revision", label: "当前修订", value: revisionLabel.value },
          { id: "segments", label: "段落数", value: String(outlineSegments.value.length) },
          { id: "jobs", label: "AI 作业", value: String(recentJobs.value.length) }
        ],
        sections: [
          {
            id: "version",
            title: "当前脚本",
            fields: [
              { id: "title", label: "主标题", value: titleSeed.value, multiline: true },
              { id: "source", label: "来源", value: currentSourceLabel.value },
              { id: "model", label: "模型", value: currentModelLabel.value }
            ]
          },
          {
            id: "jobs",
            title: "最近作业",
            emptyLabel: "当前没有真实 AI 作业记录。",
            items: recentJobs.value.slice(0, 3).map((job) => ({
              id: job.id,
              title: capabilityLabel(job.capabilityId),
              description: `${job.provider} · ${job.model}`,
              meta: jobStatusLabel(job.status),
              tone: job.status === "failed" ? "danger" : job.status === "blocked" ? "warning" : "brand"
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

async function handleSave(): Promise<void> {
  await scriptStore.save(content.value);
}

async function handleGenerate(): Promise<void> {
  await scriptStore.generate(topic.value.trim());
}

async function handleRewrite(): Promise<void> {
  await scriptStore.rewrite(instructions.value.trim());
}

function capabilityLabel(capabilityId: string): string {
  if (capabilityId === "script_generation") return "脚本生成";
  if (capabilityId === "script_rewrite") return "脚本改写";
  return capabilityId;
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
      const title = rawTitle.replace(/^#+\s*/, "");
      const excerpt = lines.slice(1).join(" ").slice(0, 80) || "等待补充正文。";
      return {
        excerpt,
        id: `segment-${index + 1}`,
        title
      };
    });
}
</script>

<style scoped>
.script-topic-center {
  display: grid;
  gap: 20px;
}

.script-topic-center__header,
.script-topic-center__control-bar {
  align-items: flex-start;
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.script-topic-center__headline {
  display: grid;
  gap: 8px;
}

.script-topic-center__eyebrow {
  color: var(--text-tertiary);
  font-size: 12px;
  letter-spacing: 0.12em;
  margin: 0;
  text-transform: uppercase;
}

.script-topic-center__summary,
.script-topic-center__panel-heading p,
.script-topic-center__control-copy p,
.script-topic-center__brief-card p,
.script-topic-center__outline-list p,
.script-topic-center__job p,
.script-topic-center__empty-inline,
.script-topic-center__state-banner p,
.script-topic-center__editor-foot p {
  color: var(--text-secondary);
  margin: 0;
}

.script-topic-center__meta,
.script-topic-center__control-actions,
.script-topic-center__editor-meta {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.script-topic-center__chip,
.script-topic-center__mini-status,
.script-topic-center__editor-meta span {
  background: color-mix(in srgb, var(--surface-tertiary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 999px;
  color: var(--text-secondary);
  font-size: 12px;
  padding: 6px 12px;
}

.script-topic-center__chip--project {
  color: var(--text-primary);
}

.script-topic-center__chip[data-tone="ready"] {
  border-color: color-mix(in srgb, var(--color-success) 35%, var(--border-default));
  color: var(--color-success);
}

.script-topic-center__chip[data-tone="blocked"] {
  border-color: color-mix(in srgb, var(--color-warning) 35%, var(--border-default));
  color: var(--color-warning);
}

.script-topic-center__chip[data-tone="error"] {
  border-color: color-mix(in srgb, var(--color-danger) 35%, var(--border-default));
  color: var(--color-danger);
}

.script-topic-center__control-bar,
.script-topic-center__state-banner,
.script-topic-center__panel {
  background: color-mix(in srgb, var(--surface-secondary) 92%, transparent);
  border: 1px solid var(--border-default);
  border-radius: 20px;
  box-shadow: var(--shadow-sm);
}

.script-topic-center__control-bar {
  padding: 18px 20px;
}

.script-topic-center__control-copy {
  display: grid;
  gap: 6px;
}

.script-topic-center__button {
  align-items: center;
  border: 1px solid transparent;
  border-radius: 8px;
  display: inline-flex;
  gap: 8px;
  height: 40px;
  justify-content: center;
  padding: 0 16px;
}

.script-topic-center__button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.script-topic-center__button--primary {
  background: var(--brand-primary);
  color: var(--text-inverse, #041314);
}

.script-topic-center__button--ghost {
  background: transparent;
  border-color: var(--border-default);
  color: var(--text-primary);
}

.script-topic-center__button--ai {
  background: var(--gradient-ai-primary);
  color: #fff;
}

.script-topic-center__state-banner {
  align-items: center;
  display: flex;
  gap: 14px;
  padding: 14px 18px;
}

.script-topic-center__state-banner--error {
  border-color: color-mix(in srgb, var(--color-danger) 35%, var(--border-default));
}

.script-topic-center__state-banner--blocked {
  border-color: color-mix(in srgb, var(--color-warning) 35%, var(--border-default));
}

.script-topic-center__workspace {
  display: grid;
  gap: 18px;
  grid-template-columns: minmax(280px, 320px) minmax(0, 1fr) minmax(280px, 320px);
}

.script-topic-center__panel,
.script-topic-center__rail {
  display: grid;
  gap: 16px;
}

.script-topic-center__panel {
  align-content: start;
  padding: 18px;
}

.script-topic-center__panel-heading,
.script-topic-center__subheading,
.script-topic-center__editor-foot {
  align-items: center;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.script-topic-center__field {
  display: grid;
  gap: 8px;
}

.script-topic-center__field span,
.script-topic-center__brief-card small,
.script-topic-center__title-card small {
  color: var(--text-tertiary);
  font-size: 12px;
}

.script-topic-center__field input,
.script-topic-center__field textarea,
.script-topic-center__editor {
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  color: var(--text-primary);
  padding: 12px 14px;
}

.script-topic-center__field textarea {
  min-height: 132px;
  resize: vertical;
}

.script-topic-center__brief {
  display: grid;
  gap: 12px;
}

.script-topic-center__brief-card,
.script-topic-center__title-card {
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 14%, transparent), transparent 60%),
    var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 16px;
  display: grid;
  gap: 6px;
  padding: 14px;
}

.script-topic-center__outline {
  display: grid;
  gap: 12px;
}

.script-topic-center__outline-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding-left: 18px;
}

.script-topic-center__outline-list li {
  display: grid;
  gap: 4px;
}

.script-topic-center__loading,
.script-topic-center__empty {
  align-items: center;
  background: var(--surface-tertiary);
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

.script-topic-center__editor-shell {
  display: grid;
  gap: 12px;
}

.script-topic-center__editor {
  min-height: 420px;
  resize: vertical;
}

.script-topic-center__version-list,
.script-topic-center__job-list {
  display: grid;
  gap: 10px;
}

.script-topic-center__version {
  align-items: center;
  background: var(--surface-tertiary);
  border: 1px solid transparent;
  border-radius: 14px;
  display: flex;
  gap: 12px;
  justify-content: space-between;
  padding: 14px;
  text-align: left;
}

.script-topic-center__version--active {
  border-color: color-mix(in srgb, var(--brand-primary) 32%, var(--border-default));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--brand-primary) 28%, transparent);
}

.script-topic-center__version p,
.script-topic-center__version small {
  color: var(--text-secondary);
  margin: 0;
}

.script-topic-center__job {
  align-items: center;
  background: var(--surface-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 14px;
  display: flex;
  gap: 12px;
  justify-content: space-between;
  padding: 14px;
}

.script-topic-center__job span {
  border-radius: 999px;
  font-size: 12px;
  padding: 4px 10px;
}

.script-topic-center__job span[data-job-state="succeeded"] {
  background: color-mix(in srgb, var(--color-success) 16%, transparent);
  color: var(--color-success);
}

.script-topic-center__job span[data-job-state="blocked"] {
  background: color-mix(in srgb, var(--color-warning) 16%, transparent);
  color: var(--color-warning);
}

.script-topic-center__job span[data-job-state="failed"] {
  background: color-mix(in srgb, var(--color-danger) 16%, transparent);
  color: var(--color-danger);
}

.script-topic-center__job span:not([data-job-state="succeeded"]):not([data-job-state="blocked"]):not([data-job-state="failed"]) {
  background: color-mix(in srgb, var(--brand-primary) 14%, transparent);
  color: var(--brand-primary);
}

@media (max-width: 1280px) {
  .script-topic-center__workspace {
    grid-template-columns: minmax(260px, 300px) minmax(0, 1fr);
  }

  .script-topic-center__rail {
    grid-column: 1 / -1;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {
  .script-topic-center__header,
  .script-topic-center__control-bar,
  .script-topic-center__panel-heading,
  .script-topic-center__editor-foot {
    align-items: stretch;
    flex-direction: column;
  }

  .script-topic-center__workspace,
  .script-topic-center__rail {
    grid-template-columns: 1fr;
  }

  .script-topic-center__editor {
    min-height: 320px;
  }
}
</style>
