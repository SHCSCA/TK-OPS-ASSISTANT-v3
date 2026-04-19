<template>
  <div class="page-container h-full">
    <header class="page-header">
      <div class="page-header__crumb">首页 / 系统与 AI</div>
      <div class="page-header__row">
        <div>
          <h1 class="page-header__title">AI 与系统设置</h1>
          <div class="page-header__subtitle">管理运行时、缓存、模型提供商与提示词。</div>
        </div>
        <div class="page-header__actions">
          <Chip :variant="configBusStore.runtimeStatus === 'online' ? 'success' : 'danger'">
            Runtime: {{ configBusStore.runtimeStatus === 'online' ? '在线' : '离线' }}
          </Chip>
          <Button variant="secondary" @click="shellUiStore.openDetailPanel()">
            打开诊断抽屉
          </Button>
        </div>
      </div>
    </header>

    <div v-if="errorSummary" class="dashboard-alert" data-tone="danger">
      <span class="material-symbols-outlined">error</span>
      <span>{{ errorSummary }}</span>
    </div>

    <div :class="styles.settingsLayout">
      <aside :class="styles.sidebar">
        <SettingsNav v-model="currentSection" />
      </aside>

      <main :class="styles.mainCard">
        <Card :class="styles.mainCard" :padded="false">
          <div :class="styles.cardHeader">
            <span class="eyebrow">{{ sectionMeta.eyebrow }}</span>
            <h3>{{ sectionMeta.title }}</h3>
            <p class="summary">{{ sectionMeta.summary }}</p>
          </div>

          <div :class="styles.cardBody">
            <transition name="section-fade" mode="out-in">
              <div :key="currentSection" class="section-content-wrapper">
                <!-- Provider 管理 -->
                <ProviderList
                  v-if="currentSection === 'provider'"
                  :providers="providerCardStates"
                  @configure="openProviderConfig"
                  @test="handleQuickTest"
                />

                <!-- 能力绑定矩阵 -->
                <CapabilityMatrix
                  v-else-if="currentSection === 'capability'"
                  :rows="capabilityRows"
                  :provider-catalog="aiStore.providerCatalog"
                  :model-catalog="aiStore.modelCatalogByProvider"
                  :support-matrix="aiStore.supportMatrix"
                  :dirty="capabilityDirty"
                  @update="updateCapabilityRow"
                  @load-models="loadModelsForProvider"
                  @save="saveCapabilities"
                  @reset="resetCapabilities"
                />

                <!-- Prompt 模板 -->
                <PromptTemplateList
                  v-else-if="currentSection === 'prompt'"
                  :items="promptStates"
                  @toggle="togglePrompt"
                  @update="updatePrompt"
                  @reset="resetPrompt"
                  @save="savePrompt"
                />

                <!-- 音色管理 -->
                <VoiceProfileGrid
                  v-else-if="currentSection === 'voice'"
                  :model-value="systemForm.ai.voice"
                  @update:model-value="val => updateSystemForm({ ai: { voice: val } })"
                  v-model:selected-provider-id="selectedTtsProviderId"
                  :profiles="voiceProfiles"
                  :providers="ttsProviders"
                  :previewing-id="previewingVoiceId"
                  @preview="previewVoice"
                />

                <!-- 系统设置表单（目录/缓存/日志/字幕） -->
                <div v-else-if="['directory', 'cache', 'logging', 'subtitle'].includes(currentSection)" class="form-container">
                  <SettingsSystemFormPanel
                    :current-section="currentSection"
                    :form="systemForm"
                    :disabled="configBusStore.status === 'saving'"
                    @update="updateSystemForm"
                    @pick-directory="handlePickDirectory"
                  />
                  <div class="form-footer">
                    <Button variant="primary" :disabled="!systemDirty" @click="saveSystemSettings">
                      保存系统设置
                    </Button>
                  </div>
                </div>

                <!-- 诊断工作台 -->
                <section v-else-if="currentSection === 'diagnostics'" :class="styles.diagnosticGrid">
                  <Card :class="styles.diagnosticTile" :interactive="false">
                    <span>Runtime 版本</span>
                    <strong>{{ configBusStore.health?.version || '-' }}</strong>
                    <p>{{ configBusStore.health?.service || '未读取' }}</p>
                  </Card>
                  <Card :class="styles.diagnosticTile" :interactive="false">
                    <span>配置修订</span>
                    <strong>{{ configBusStore.settings?.revision ?? '-' }}</strong>
                    <p>最后同步: {{ formatDate(configBusStore.lastSyncedAt) }}</p>
                  </Card>
                  <Card :class="styles.diagnosticTile" :interactive="false">
                    <span>Provider 连通</span>
                    <strong>{{ configuredProviderCount }}/{{ aiStore.providerCatalog.length }}</strong>
                    <p>已保存连接凭据</p>
                  </Card>
                  <Card :class="styles.diagnosticTile" :interactive="false">
                    <span>已启用能力</span>
                    <strong>{{ enabledCapabilityCount }}</strong>
                    <p>共 7 项核心能力</p>
                  </Card>
                  <Card :class="styles.diagnosticTile" :interactive="false">
                    <span>运行时长</span>
                    <strong>{{ uptimeLabel }}</strong>
                    <p>端口 {{ configBusStore.health?.runtime?.port ?? '-' }}</p>
                  </Card>
                  <Card :class="styles.diagnosticTile" :interactive="false">
                    <span>诊断导出</span>
                    <strong>
                      <Button variant="secondary" size="sm" @click="exportDiagnostics">
                        <template #leading><span class="material-symbols-outlined">download</span></template>
                        导出诊断包
                      </Button>
                    </strong>
                    <p>{{ configBusStore.diagnostics?.mode ?? '-' }} 模式</p>
                  </Card>
                </section>
              </div>
            </transition>
          </div>
        </Card>
      </main>
    </div>

    <!-- Provider 配置抽屉 -->
    <ProviderConfigDrawer
      :open="isDrawerOpen"
      :provider="activeProvider"
      :is-testing="isTestingProvider"
      :is-refreshing="isRefreshingModels"
      :is-saving="isSavingProvider"
      @close="isDrawerOpen = false"
      @save="saveProviderConfig"
      @test="handleProviderTest"
      @refresh-models="refreshProviderModels"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import styles from "./AISystemSettings.module.css";
import type { SettingsSectionId } from "./types";

// Composables
import { useProviderManagement } from "./use-provider-management";
import { useCapabilityBinding } from "./use-capability-binding";
import { usePromptEditing } from "./use-prompt-editing";
import { useVoiceProfiles } from "./use-voice-profiles";
import { useSystemSettings } from "./use-system-settings";

// 子组件
import SettingsNav from "./components/SettingsNav.vue";
import ProviderList from "./components/ProviderList.vue";
import ProviderConfigDrawer from "./components/ProviderConfigDrawer.vue";
import CapabilityMatrix from "./components/CapabilityMatrix.vue";
import PromptTemplateList from "./components/PromptTemplateList.vue";
import VoiceProfileGrid from "./components/VoiceProfileGrid.vue";
import SettingsSystemFormPanel from "@/modules/settings/components/SettingsSystemFormPanel.vue";

// Stores
import { useAICapabilityStore } from "@/stores/ai-capability";
import { useConfigBusStore } from "@/stores/config-bus";
import { useShellUiStore } from "@/stores/shell-ui";
import { fetchVoiceProfiles } from "@/app/runtime-client";

// UI 组件
import Button from "@/components/ui/Button/Button.vue";
import Card from "@/components/ui/Card/Card.vue";
import Chip from "@/components/ui/Chip/Chip.vue";

const aiStore = useAICapabilityStore();
const configBusStore = useConfigBusStore();
const shellUiStore = useShellUiStore();

const currentSection = ref<SettingsSectionId>("provider");

// 使用 composables
const {
  isDrawerOpen,
  activeProvider,
  isTestingProvider,
  isRefreshingModels,
  isSavingProvider,
  providerCardStates,
  openProviderConfig,
  handleQuickTest,
  handleProviderTest,
  saveProviderConfig,
  refreshProviderModels,
  loadModelsForProvider
} = useProviderManagement();

const {
  capabilityRows,
  capabilityDirty,
  updateCapabilityRow,
  saveCapabilities,
  resetCapabilities
} = useCapabilityBinding();

const {
  promptStates,
  togglePrompt,
  updatePrompt,
  resetPrompt,
  savePrompt
} = usePromptEditing(capabilityRows);

const {
  selectedTtsProviderId,
  selectedVoiceId,
  previewingVoiceId,
  ttsProviders,
  voiceProfiles,
  previewVoice
} = useVoiceProfiles();

const {
  systemForm,
  systemDirty,
  updateSystemForm,
  handlePickDirectory,
  saveSystemSettings
} = useSystemSettings();

// 区块元信息
const SECTION_META: Record<SettingsSectionId, { eyebrow: string; title: string; summary: string }> = {
  provider: { eyebrow: "AI 提供商", title: "管理 Provider 注册表与连接凭据", summary: "配置 API Key 和 Base URL，通过实时探针验证连通性。" },
  capability: { eyebrow: "能力策略", title: "将 7 项 AI 能力分别绑定到 Provider 与模型", summary: "能力绑定决定了脚本生成、配音等功能具体使用哪个模型。" },
  prompt: { eyebrow: "Prompt 模板", title: "为每项 AI 能力配置角色设定与模板", summary: "支持变量高亮和多版本回退。" },
  voice: { eyebrow: "媒体设置", title: "音色管理与试听", summary: "音色来源由 Provider 决定，切换 Provider 后需重新选择。" },
  subtitle: { eyebrow: "媒体设置", title: "字幕生成与对齐策略", summary: "" },
  directory: { eyebrow: "系统总线", title: "核心路径设置", summary: "" },
  cache: { eyebrow: "系统总线", title: "存储与缓存清理", summary: "" },
  logging: { eyebrow: "系统总线", title: "日志级别与保留策略", summary: "" },
  diagnostics: { eyebrow: "运行视图", title: "诊断工作台", summary: "实时监控 Runtime 连通性、配置修订号和授权状态。" }
};

const sectionMeta = computed(() => SECTION_META[currentSection.value]);

const configuredProviderCount = computed(() => aiStore.providerCatalog.filter(p => p.configured).length);
const enabledCapabilityCount = computed(() => capabilityRows.value.filter(r => r.enabled).length);

const uptimeLabel = computed(() => {
  const ms = configBusStore.health?.runtime?.uptimeMs;
  if (!ms) return "-";
  const hours = Math.floor(ms / 3600000);
  const minutes = Math.floor((ms % 3600000) / 60000);
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
});

const errorSummary = computed(() => {
  if (configBusStore.error) return configBusStore.error.message;
  if (aiStore.error) return aiStore.error.message;
  return null;
});

function formatDate(val?: string) {
  return val ? new Date(val).toLocaleDateString("zh-CN") : "-";
}

async function exportDiagnostics() {
  // 调用诊断导出接口——后续接入 runtime-client
  shellUiStore.openDetailPanel();
}

onMounted(async () => {
  await Promise.all([
    aiStore.loadProviderCatalog(),
    aiStore.load(),
    aiStore.loadSupportMatrix(),
    configBusStore.load()
  ]);
  if (aiStore.providerCatalog.length > 0) {
    void aiStore.loadProviderModels(aiStore.providerCatalog[0].provider);
  }
});
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
  margin-bottom: var(--space-6);
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

.summary {
  margin: 0;
  font: var(--font-body-sm);
  color: var(--color-text-secondary);
}

.eyebrow {
  display: block;
  font: var(--font-caption);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  margin-bottom: 4px;
}

.form-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border-subtle);
}

.section-fade-enter-active,
.section-fade-leave-active {
  transition: opacity var(--motion-default) var(--ease-standard), transform var(--motion-default) var(--ease-spring);
}

.section-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.section-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.section-content-wrapper {
  width: 100%;
}
</style>
