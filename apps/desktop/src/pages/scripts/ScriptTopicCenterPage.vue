<template>
  <ProjectContextGuard>
    <div class="page-container">
      <header class="page-header">
        <div class="page-header__crumb">首页 / 创作策划</div>
        <div class="page-header__row">
          <div>
            <h1 class="page-header__title">脚本与选题中心</h1>
            <div class="page-header__subtitle">主题、脚本、版本和 AI 改写继续挂在同一个项目链路上，不再拆成零散表单。</div>
          </div>
          <div class="page-header__actions">
            <!-- 风格预设(mock) -->
            <Button variant="secondary" disabled>风格预设 ▾</Button>
            <Button variant="ai" :running="scriptStore.status === 'generating'" :disabled="generateDisabled" @click="handleGenerate">
              <template #leading><span class="material-symbols-outlined">auto_awesome</span></template>
              AI 生成脚本
            </Button>
            <Button variant="secondary" @click="handleCopyContent" :disabled="!content">
              <template #leading><span class="material-symbols-outlined">content_copy</span></template>
              复制正文
            </Button>
            <Button variant="primary" :disabled="saveDisabled" data-action="save-script" @click="handleSave">
              <template #leading><span class="material-symbols-outlined">save</span></template>
              保存脚本
            </Button>
          </div>
        </div>
      </header>

      <div class="script-workspace">
        <!-- 左侧 Prompt 面板 -->
        <aside class="script-panel script-panel--prompt" data-script-section="prompt-panel">
          <Card class="script-card h-full">
            <div class="script-card__header">
              <h3>策划工作台</h3>
            </div>
            <div class="script-card__body">
              <div class="form-group">
                <Input v-model="topic" label="主题" placeholder="例如：春日新品种草" :disabled="isBusy" />
              </div>
              <div class="form-group">
                <Input v-model="instructions" label="改写要求" multiline :rows="6" placeholder="补充目标人群、时长和风格要求" :disabled="isBusy" />
              </div>

              <!-- 结构锚点 -->
              <div class="outline-section">
                <div class="outline-header">
                  <strong>结构锚点</strong>
                  <Chip size="sm">{{ outlineSegments.length }} 段</Chip>
                </div>
                <div v-if="outlineSegments.length > 0" class="outline-list">
                  <div v-for="seg in outlineSegments" :key="seg.id" class="outline-item">
                    <strong>{{ seg.title }}</strong>
                    <p>{{ seg.excerpt }}</p>
                  </div>
                </div>
                <div v-else class="empty-text">还没有正文结构，先生成脚本或从现有版本继续编辑。</div>
              </div>
            </div>
            <div class="script-card__footer">
               <Button variant="secondary" block :disabled="rewriteDisabled" @click="handleRewrite">改写当前版本</Button>
            </div>
          </Card>
        </aside>

        <!-- 中间 脚本编辑器 -->
        <main class="script-panel script-panel--editor" data-script-section="editor">
          <Card class="script-card h-full editor-card" :class="{ 'is-generating': scriptStore.status === 'generating' }">
             <!-- AI 生成流光线 -->
             <div class="ai-flow-bar" v-if="scriptStore.status === 'generating'"></div>

             <div class="editor-header">
                <div>
                   <h3>脚本工作面</h3>
                   <span class="editor-meta">{{ displayedVersionMeta }}</span>
                </div>
                <div class="editor-tags">
                   <Chip v-if="currentSourceLabel">{{ currentSourceLabel }}</Chip>
                   <Chip v-if="currentModelLabel" variant="brand">{{ currentModelLabel }}</Chip>
                </div>
             </div>

             <div class="editor-body">
               <div v-if="pageState === 'loading'" class="editor-empty">
                 <span class="material-symbols-outlined spinning">progress_activity</span>
                 <p>正在通过 Runtime 拉取当前项目脚本...</p>
               </div>
               <div v-else-if="pageState === 'empty'" class="editor-empty">
                 <span class="material-symbols-outlined">description</span>
                 <p>当前项目还没有脚本版本<br/><small>先填写主题后生成脚本，或等待 Script Studio 写入首个版本。</small></p>
               </div>
               <textarea v-else
                 class="editor-textarea"
                 data-field="script.content"
                 v-model="content"
                 :disabled="isBusy || pageState === 'empty'"
               />
             </div>

             <div class="editor-footer">
                <span>当前共 {{ contentLength }} 字，按真实段落拆成 {{ outlineSegments.length }} 个策划锚点。</span>
                <span>{{ updatedAtLabel }}</span>
             </div>
          </Card>
        </main>

        <!-- 右侧 版本与变体 -->
        <aside class="script-panel script-panel--versions" data-script-section="versions">
          <Card class="script-card rail-card" style="flex: 1; min-height: 0;">
            <div class="script-card__header">
              <h3>版本轨迹</h3>
              <Chip size="sm">{{ versions.length }}</Chip>
            </div>
            <div class="script-card__body no-padding scroll-area">
               <div v-if="versions.length === 0" class="empty-text">当前项目还没有脚本版本。</div>
               <div v-else class="version-list">
                 <transition-group name="list-fade">
                   <div v-for="version in versions" :key="version.revision"
                     class="version-item"
                     data-script-version-item
                     :class="{ 'is-active': selectedRevision === version.revision }"
                     @click="selectedRevision = version.revision">
                      <div class="v-main">
                        <strong>修订 {{ version.revision }}</strong>
                        <div class="v-actions">
                           <Button
                             v-if="currentVersion?.revision !== version.revision"
                             variant="secondary"
                             size="xs"
                             :disabled="isBusy"
                             @click.stop="handleAdopt(version.revision)">
                             采用
                           </Button>
                           <Chip v-else variant="success" size="sm">当前采用</Chip>
                        </div>
                      </div>
                      <div class="v-meta">
                        <span class="v-time">{{ formatDateTime(version.createdAt) }}</span>
                        <span class="v-source">{{ version.source }} · {{ version.provider ?? "手动" }}</span>
                      </div>
                   </div>
                 </transition-group>
               </div>
            </div>
          </Card>

          <Card class="script-card rail-card" data-script-section="title-variants">
             <div class="script-card__header">
              <h3>AI 作业与变体</h3>
            </div>
            <div class="script-card__body no-padding">
              <div class="title-seed">
                 <small>当前主标题</small>
                 <strong>{{ titleSeed }}</strong>
              </div>

              <div v-if="recentJobs.length === 0" class="empty-text">当前还没有真实 AI 作业记录。</div>
              <div v-else class="job-list">
                 <transition-group name="list-fade">
                   <div v-for="job in recentJobs.slice(0, 3)" :key="job.id" class="job-item">
                      <div class="job-main">
                         <strong>{{ capabilityLabel(job.capabilityId) }}</strong>
                         <span>{{ job.provider }} · {{ job.model }}</span>
                      </div>
                      <Chip :variant="jobTone(job.status)" size="sm">{{ jobStatusLabel(job.status) }}</Chip>
                   </div>
                 </transition-group>
              </div>
            </div>
          </Card>
        </aside>
      </div>
    </div>
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

import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";
import Input from "@/components/ui/Input/Input.vue";

type PageState = "loading" | "empty" | "ready" | "error" | "blocked";
type Tone = "neutral" | "brand" | "success" | "warning" | "danger" | "info" | "default";

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

const revisionLabel = computed(() => currentVersion.value ? `修订 ${currentVersion.value.revision}` : "尚无修订");
const pageStateLabel = computed(() => {
  const map: Record<PageState, string> = { blocked: "能力阻断", empty: "空态", error: "错误", loading: "加载中", ready: "已就绪" };
  return map[pageState.value];
});

const pageStateDescription = computed(() => {
  if (pageState.value === "loading") return "当前页面正在通过真实 Runtime 读取脚本版本和 AI 作业。";
  if (pageState.value === "empty") return "还没有脚本版本时，不展示伪造策划结果，只保留真实生成入口。";
  if (pageState.value === "error") return scriptStore.error?.message || "脚本请求失败，请稍后重试。";
  if (pageState.value === "blocked") return latestJob.value?.error ?? "最近一次 AI 作业被阻断，当前仍可继续手动编辑与保存。";
  return "当前页面使用真实项目、脚本版本和 AI 作业状态构成策划工作台。";
});

const statusLabel = computed(() => {
  if (scriptStore.status === 'generating') return "正在生成...";
  if (scriptStore.status === 'saving') return "正在保存...";
  if (scriptStore.status === 'ready') return "已保存";
  if (scriptStore.status === 'error') return "失败";
  return "就绪";
});

const statusTone = computed(() => {
  if (scriptStore.status === 'generating') return "brand";
  if (scriptStore.status === 'saving') return "info";
  if (scriptStore.status === 'ready') return "success";
  if (scriptStore.status === 'error') return "danger";
  return "default";
});

const generateDisabled = computed(() => isBusy.value || topic.value.trim().length === 0);
const rewriteDisabled = computed(() => isBusy.value || instructions.value.trim().length === 0 || !hasDocument.value);
const saveDisabled = computed(() => isBusy.value || content.value.trim().length === 0 || pageState.value === "empty");
const contentLength = computed(() => content.value.trim().length);
const outlineSegments = computed(() => parseScriptSegments(content.value));
const titleSeed = computed(() => outlineSegments.value[0]?.title ?? "等待真实脚本标题");

const displayedVersionMeta = computed(() => {
  if (!displayedVersion.value) return "暂无脚本版本，等待当前项目写入正文。";
  return `修订 ${displayedVersion.value.revision} · ${formatDateTime(displayedVersion.value.createdAt)}`;
});
const currentSourceLabel = computed(() => displayedVersion.value?.source ?? "无来源");
const currentModelLabel = computed(() => displayedVersion.value?.model ?? "手动编辑");
const updatedAtLabel = computed(() => displayedVersion.value ? `写入时间 ${formatDateTime(displayedVersion.value.createdAt)}` : "尚未写入");

watch(currentProjectId, (projectId, previousProjectId) => {
  if (!projectId || projectId === previousProjectId) return;
  topic.value = "";
  instructions.value = "";
  selectedRevision.value = null;
  void scriptStore.load(projectId);
}, { immediate: true });

watch(currentVersion, (value) => { selectedRevision.value = value?.revision ?? null; }, { immediate: true });
watch(displayedVersion, (value) => { content.value = value?.content ?? ""; }, { immediate: true });

watch([projectName, revisionLabel, pageState, latestJob, currentVersion, titleSeed], () => {
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
            tone: jobTone(job.status)
          }))
        }
      ]
    })
  );
}, { immediate: true });

onBeforeUnmount(() => {
  shellUiStore.clearDetailContext("contextual");
});

async function handleSave(): Promise<void> { await scriptStore.save(content.value); }
async function handleGenerate(): Promise<void> { await scriptStore.generate(topic.value.trim()); }
async function handleRewrite(): Promise<void> { await scriptStore.rewrite(instructions.value.trim()); }

async function handleAdopt(revision: number) {
  if (!confirm(`确定要采用「修订 ${revision}」作为当前项目的主脚本吗？`)) return;
  await scriptStore.adoptVersion(revision);
}

async function handleCopyContent() {
  if (!content.value) return;
  try {
    await navigator.clipboard.writeText(content.value);
    // Optional: show a toast or feedback
  } catch (err) {
    console.error("Failed to copy script:", err);
  }
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

function jobTone(status: string): Tone {
  if (status === "failed") return "danger";
  if (status === "blocked") return "warning";
  if (status === "succeeded") return "success";
  if (status === "running") return "brand";
  return "default";
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
    const title = rawTitle.replace(/^#+\s*/, "");
    const excerpt = lines.slice(1).join(" ").slice(0, 80) || "等待补充正文。";
    return { excerpt, id: `segment-${index + 1}`, title };
  });
}
</script>

<style scoped src="./ScriptTopicCenterPage.css"></style>
