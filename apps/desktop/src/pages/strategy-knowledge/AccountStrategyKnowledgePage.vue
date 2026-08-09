<template>
  <main
    class="strategy-knowledge-page"
    data-testid="strategy-knowledge-page"
    :data-state="pageDataState"
  >
    <section
      v-if="!activeAccountId"
      class="sk-page-state"
      data-state="dependency_blocked"
    >
      <span class="material-symbols-outlined" aria-hidden="true">person_off</span>
      <h1>请先选择账号</h1>
      <p>定位、知识来源和 BrandKit 都以账号为隔离边界。</p>
    </section>

    <section
      v-else-if="cache?.pageState === 'loading' || cache?.pageState === 'idle'"
      class="sk-page-state"
      data-state="loading"
    >
      <span class="sk-spinner sk-spinner--large" aria-hidden="true" />
      <h1>正在读取账号配置</h1>
      <p>仅加载当前账号的定位与知识数据。</p>
    </section>

    <section
      v-else-if="cache?.pageState === 'error'"
      class="sk-page-state"
      data-state="error"
    >
      <span class="material-symbols-outlined" aria-hidden="true">error</span>
      <h1>定位与知识暂时无法加载</h1>
      <p>{{ cache.error?.message }}</p>
      <small v-if="cache.error?.logId">日志 {{ cache.error.logId }}</small>
      <button class="sk-button sk-button--primary" type="button" @click="reload">
        重试
      </button>
    </section>

    <template v-else-if="cache">
      <header class="sk-page-header">
        <div>
          <h1 class="sr-only">定位与知识</h1>
          <p>先固定内容方向，再让每次生成使用同一份知识边界。</p>
        </div>
        <div class="sk-header-actions">
          <button
            v-if="fromAccountWizard"
            class="sk-button sk-button--secondary"
            data-testid="return-account-wizard"
            type="button"
            @click="returnToAccountWizard"
          >
            <span class="material-symbols-outlined" aria-hidden="true">arrow_back</span>
            返回账号向导
          </button>
          <button class="sk-button sk-button--secondary" type="button" @click="reload">
            <span class="material-symbols-outlined" aria-hidden="true">refresh</span>
            刷新
          </button>
        </div>
      </header>

      <div
        v-if="cache.pageState === 'first_use'"
        class="sk-first-use"
        data-state="first_use"
      >
        <span class="material-symbols-outlined" aria-hidden="true">auto_awesome</span>
        <div>
          <strong>从账号定位开始</strong>
          <p>这里还没有配置。创建定位版本，并添加真实知识来源即可。</p>
        </div>
        <button
          class="sk-button sk-button--primary"
          type="button"
          @click="store.openPositioningEditor(activeAccountId)"
        >
          新建定位
        </button>
      </div>

      <div v-if="cache.error" class="sk-feedback sk-feedback--error" data-state="error">
        <span class="material-symbols-outlined" aria-hidden="true">warning</span>
        <div>
          <strong>{{ cache.error.message }}</strong>
          <small v-if="cache.error.logId">日志 {{ cache.error.logId }}</small>
        </div>
        <button
          v-if="cache.error.retryable"
          class="sk-button sk-button--text"
          type="button"
          @click="reload"
        >
          重试
        </button>
        <button
          class="sk-icon-button"
          type="button"
          aria-label="关闭错误提示"
          @click="store.clearFeedback(activeAccountId)"
        >
          <span class="material-symbols-outlined" aria-hidden="true">close</span>
        </button>
      </div>

      <div v-if="cache.feedback" class="sk-feedback" role="status">
        <span class="material-symbols-outlined" aria-hidden="true">check_circle</span>
        <span>{{ cache.feedback }}</span>
        <button
          class="sk-icon-button"
          type="button"
          aria-label="关闭状态提示"
          @click="store.clearFeedback(activeAccountId)"
        >
          <span class="material-symbols-outlined" aria-hidden="true">close</span>
        </button>
      </div>

      <div class="sk-grid">
        <PositioningPanel
          :cache="cache"
          @open-editor="store.openPositioningEditor(activeAccountId)"
          @cancel-editor="store.closePositioningEditor(activeAccountId)"
          @edit-version="editPositioningVersion"
          @open-detail="openPositioningDetail"
          @update-draft="updatePositioningDraft"
          @create="store.createPositioning(activeAccountId)"
          @activate="store.activatePositioning(activeAccountId, $event)"
        />
        <BrandKitPanel :kit="cache.brandKit" />
        <KnowledgeRulesPanel
          :cache="cache"
          @update="updateRulesDraft"
          @save="store.saveRules(activeAccountId)"
        />
        <KnowledgeSourcesPanel
          :cache="cache"
          @open-editor="store.openSourceEditor(activeAccountId)"
          @cancel-editor="store.closeSourceEditor(activeAccountId)"
          @update-draft="updateSourceDraft"
          @add-source="store.addSourceFromDraft(activeAccountId)"
          @start-index="store.startIndex(activeAccountId)"
          @index-source="store.startIndex(activeAccountId, [$event])"
          @remove-source="removeSource"
          @filter="store.applyFilters(activeAccountId, $event)"
          @refresh="reload"
        />
      </div>

      <PositioningVersionDetailPanel
        :cache="cache"
        @activate="store.activatePositioning(activeAccountId, $event)"
        @close="store.closePositioningDetail(activeAccountId)"
        @edit="editPositioningVersion"
        @retry="retryPositioningDetail"
      />
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, inject, onBeforeUnmount, watch } from "vue";
import { routeLocationKey, routerKey } from "vue-router";

import { requestDesktopConfirm } from "@/composables/useDesktopConfirm";
import type { AccountWorkspaceContextDto } from "@/types/runtime/accounts";
import BrandKitPanel from "@/modules/knowledge/BrandKitPanel.vue";
import KnowledgeRulesPanel from "@/modules/knowledge/KnowledgeRulesPanel.vue";
import KnowledgeSourcesPanel from "@/modules/knowledge/KnowledgeSourcesPanel.vue";
import PositioningPanel from "@/modules/knowledge/PositioningPanel.vue";
import PositioningVersionDetailPanel from "@/modules/knowledge/PositioningVersionDetailPanel.vue";
import { accountUnsavedGuardRegistrarKey } from "@/modules/accounts/account-guard-port";
import {
  createAccountKnowledgeUnsavedGuard,
  logKnowledgeError,
  useAccountKnowledgeStore,
  type AccountUnsavedGuardRegister,
  type KnowledgeSourceDraft
} from "@/modules/knowledge";

const props = withDefaults(defineProps<{
  accountId?: string | null;
  workspaceContext?: AccountWorkspaceContextDto | null;
  registerUnsavedGuard?: AccountUnsavedGuardRegister | null;
}>(), {
  accountId: null,
  workspaceContext: null,
  registerUnsavedGuard: null
});

const store = useAccountKnowledgeStore();
const injectedGuardRegistrar = inject(accountUnsavedGuardRegistrarKey, null);
const route = inject(routeLocationKey, null);
const router = inject(routerKey, null);
const activeAccountId = computed(() => props.accountId ?? "");
const cache = computed(() => props.accountId ? store.cache(props.accountId) : null);
const pageDataState = computed(() => {
  if (!activeAccountId.value) return "dependency_blocked";
  return cache.value?.pageState === "idle"
    ? "loading"
    : cache.value?.pageState ?? "loading";
});
const fromAccountWizard = computed(() => {
  const source = route?.query.from;
  return activeAccountId.value.length > 0
    && (Array.isArray(source) ? source[0] : source) === "account-wizard";
});
let unregisterGuard: (() => void) | null = null;

watch(
  () => props.accountId,
  (accountId) => {
    if (accountId) void store.load(accountId);
  },
  { immediate: true }
);

watch(
  () => [props.accountId, props.workspaceContext?.account.revision] as const,
  ([accountId, revision], [previousAccountId, previousRevision]) => {
    if (
      accountId
      && accountId === previousAccountId
      && revision !== undefined
      && revision !== previousRevision
      && store.cache(accountId).positioning?.revision !== revision
    ) {
      void store.load(accountId);
    }
  }
);

watch(
  () => [props.accountId, props.registerUnsavedGuard] as const,
  ([accountId, propRegister]) => {
    releaseUnsavedGuard();
    if (!accountId || (!propRegister && !injectedGuardRegistrar)) return;
    try {
      const guard = createAccountKnowledgeUnsavedGuard(store, accountId);
      unregisterGuard = propRegister
        ? propRegister(guard)
        : injectedGuardRegistrar!.register(guard);
    } catch (error) {
      store.setError(accountId, error, "未保存守卫注册失败，请刷新工作区。");
    }
  },
  { immediate: true }
);

onBeforeUnmount(releaseUnsavedGuard);

function reload(): void {
  if (props.accountId) void store.load(props.accountId);
}

function openPositioningDetail(version: number): void {
  if (props.accountId) {
    void store.openPositioningDetail(props.accountId, version);
  }
}

function retryPositioningDetail(): void {
  const version = cache.value?.positioningDetailVersion;
  if (props.accountId && version) {
    void store.openPositioningDetail(props.accountId, version, true);
  }
}

function editPositioningVersion(version: number): void {
  if (props.accountId) {
    void store.editFromPositioningVersion(props.accountId, version);
  }
}

function updatePositioningDraft(
  field: Parameters<typeof store.updatePositioningDraft>[1],
  value: string
): void {
  if (props.accountId) store.updatePositioningDraft(props.accountId, field, value);
}

function updateRulesDraft(
  field: Parameters<typeof store.updateRulesDraft>[1],
  value: string
): void {
  if (props.accountId) store.updateRulesDraft(props.accountId, field, value);
}

function updateSourceDraft(
  field: keyof KnowledgeSourceDraft,
  value: KnowledgeSourceDraft[keyof KnowledgeSourceDraft]
): void {
  if (!props.accountId) return;
  if (field === "mode") {
    store.updateSourceDraft(props.accountId, field, value as KnowledgeSourceDraft["mode"]);
    return;
  }
  store.updateSourceDraft(
    props.accountId,
    field as Exclude<keyof KnowledgeSourceDraft, "mode">,
    value as string
  );
}

async function removeSource(sourceId: string): Promise<void> {
  if (!props.accountId) return;
  const confirmed = await requestDesktopConfirm(
    "确认移除此知识来源吗？来源会软删除，已有快照证据仍保留。",
    { title: "移除知识来源", kind: "warning" }
  );
  if (confirmed) await store.removeSource(props.accountId, sourceId);
}

async function returnToAccountWizard(): Promise<void> {
  if (!router || !activeAccountId.value) return;
  try {
    await router.push({
      path: "/settings/accounts",
      query: {
        action: "continue",
        account: activeAccountId.value
      }
    });
  } catch (error) {
    store.setError(
      activeAccountId.value,
      error,
      "返回账号向导失败，请从账号管理继续。"
    );
  }
}

function releaseUnsavedGuard(): void {
  if (!unregisterGuard) return;
  try {
    unregisterGuard();
  } catch (error) {
    logKnowledgeError("未保存守卫注销失败", error);
  } finally {
    unregisterGuard = null;
  }
}
</script>

<style src="./strategy-knowledge.css"></style>
<style src="./strategy-knowledge-sources.css"></style>
