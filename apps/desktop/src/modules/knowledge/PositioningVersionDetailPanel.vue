<template>
  <Teleport to="body">
    <div
      v-if="cache.positioningDetailOpen"
      class="positioning-detail-backdrop"
      @mousedown.self="emit('close')"
    >
      <aside
        class="positioning-detail-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="positioning-detail-title"
        data-testid="positioning-detail-panel"
      >
        <header class="positioning-detail-panel__header">
          <div>
            <p class="sk-eyebrow">定位版本</p>
            <h2 id="positioning-detail-title">
              v{{ cache.positioningDetailVersion ?? "-" }} 详情
            </h2>
          </div>
          <button
            class="sk-icon-button"
            type="button"
            aria-label="关闭定位详情"
            @click="emit('close')"
          >
            <span class="material-symbols-outlined" aria-hidden="true">close</span>
          </button>
        </header>

        <div
          v-if="cache.positioningDetailState === 'loading'"
          class="positioning-detail-state"
          data-state="loading"
        >
          <span class="sk-spinner sk-spinner--large" aria-hidden="true" />
          <strong>正在读取定位版本</strong>
          <p>只加载当前账号的 v{{ cache.positioningDetailVersion }}。</p>
        </div>

        <div
          v-else-if="cache.positioningDetailState === 'error'"
          class="positioning-detail-state positioning-detail-state--error"
          data-state="error"
        >
          <span class="material-symbols-outlined" aria-hidden="true">error</span>
          <strong>{{ cache.positioningDetailError?.message }}</strong>
          <small v-if="cache.positioningDetailError?.logId">
            日志 {{ cache.positioningDetailError.logId }}
          </small>
          <button
            class="sk-button sk-button--primary"
            type="button"
            @click="emit('retry')"
          >
            重新加载
          </button>
        </div>

        <template v-else-if="detail">
          <div class="positioning-detail-panel__body">
            <section class="positioning-detail-summary">
              <div>
                <span :class="`sk-pill sk-pill--${detail.status}`">
                  {{ statusLabel(detail.status) }}
                </span>
                <time>{{ formatKnowledgeDate(detail.createdAt) }}</time>
              </div>
              <strong>{{ detail.summary }}</strong>
            </section>

            <DetailSection title="目标受众" :text="audience" />
            <DetailSection
              title="内容支柱"
              :items="detail.contentPillars"
            />
            <DetailSection title="表达语气" :text="tone" :tags="toneTags" />
            <DetailSection
              title="禁用主题"
              :items="detail.prohibitedTopics"
            />
            <DetailSection title="发布约束" :text="publishingConstraints" />

            <section class="positioning-detail-section">
              <h3>追溯信息</h3>
              <dl class="positioning-detail-meta">
                <div>
                  <dt>激活时间</dt>
                  <dd>{{ formatKnowledgeDate(detail.activatedAt) }}</dd>
                </div>
                <div>
                  <dt>内容哈希</dt>
                  <dd class="positioning-hash-row">
                    <code :title="detail.contentHash">{{ hashPreview }}</code>
                    <button
                      class="sk-button sk-button--text"
                      type="button"
                      :aria-label="`复制定位版本 v${detail.version} 的完整内容哈希`"
                      @click="copyContentHash"
                    >
                      {{ copyLabel }}
                    </button>
                  </dd>
                </div>
              </dl>
              <p
                v-if="copyState === 'error'"
                class="positioning-copy-error"
                role="alert"
              >
                复制失败，请检查系统剪贴板权限后重试。
              </p>
            </section>
          </div>

          <footer class="positioning-detail-panel__actions">
            <button
              class="sk-button sk-button--text"
              type="button"
              @click="emit('close')"
            >
              关闭
            </button>
            <button
              class="sk-button sk-button--secondary"
              type="button"
              @click="emit('edit', detail.version)"
            >
              基于此版本修改
            </button>
            <button
              v-if="detail.status === 'draft'"
              class="sk-button sk-button--primary"
              type="button"
              :disabled="Boolean(cache.busyKey)"
              @click="emit('activate', detail.version)"
            >
              设为使用中
            </button>
          </footer>
        </template>
      </aside>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import {
  computed,
  defineComponent,
  h,
  ref,
  watch,
  type PropType
} from "vue";

import type { AccountKnowledgeCache } from "./account-knowledge-types";
import { formatKnowledgeDate } from "./knowledge-view-helpers";
import {
  objectDescription,
  positioningHashPreview,
  positioningToneTags
} from "./positioning-view-helpers";
import "./positioning-detail.css";

const props = defineProps<{ cache: AccountKnowledgeCache }>();
const emit = defineEmits<{
  activate: [version: number];
  close: [];
  edit: [version: number];
  retry: [];
}>();
const copyState = ref<"idle" | "success" | "error">("idle");

const detail = computed(() =>
  props.cache.positioningDetailState === "ready"
    ? props.cache.positioningDetail
    : null
);
const audience = computed(() =>
  objectDescription(detail.value?.audience ?? {}) || "未配置"
);
const tone = computed(() =>
  objectDescription(detail.value?.tone ?? {}) || "未配置"
);
const toneTags = computed(() =>
  positioningToneTags(detail.value?.tone ?? {})
);
const publishingConstraints = computed(() =>
  objectDescription(detail.value?.publishingConstraints ?? {}, true)
    || "未配置"
);
const hashPreview = computed(() =>
  positioningHashPreview(detail.value?.contentHash ?? "")
);
const copyLabel = computed(() =>
  copyState.value === "success" ? "已复制" : "复制完整哈希"
);

watch(
  () => detail.value?.version,
  () => {
    copyState.value = "idle";
  }
);

const DetailSection = defineComponent({
  name: "PositioningDetailSection",
  props: {
    title: { type: String, required: true },
    text: { type: String, default: "" },
    items: {
      type: Array as PropType<string[]>,
      default: () => []
    },
    tags: {
      type: Array as PropType<string[]>,
      default: () => []
    }
  },
  setup(sectionProps) {
    return () => h("section", { class: "positioning-detail-section" }, [
      h("h3", sectionProps.title),
      sectionProps.items.length
        ? h("div", { class: "positioning-detail-tags" },
            sectionProps.items.map((item) => h("span", { key: item }, item)))
        : h("p", sectionProps.text || "未配置"),
      sectionProps.tags.length
        ? h("div", { class: "positioning-detail-tags positioning-detail-tags--tone" },
            sectionProps.tags.map((tag) => h("span", { key: tag }, `#${tag}`)))
        : null
    ]);
  }
});

function statusLabel(status: string): string {
  return status === "active" ? "使用中" : status === "draft" ? "草稿" : "已归档";
}

async function copyContentHash(): Promise<void> {
  const selected = detail.value;
  if (!selected) return;
  try {
    if (!navigator.clipboard) {
      throw new Error("系统剪贴板不可用。");
    }
    await navigator.clipboard.writeText(selected.contentHash);
    copyState.value = "success";
  } catch (error) {
    console.error("[定位与知识] 复制定位内容哈希失败。", {
      version: selected.version,
      error
    });
    copyState.value = "error";
  }
}
</script>
