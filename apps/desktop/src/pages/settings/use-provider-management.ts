import { computed, ref } from "vue";
import { useAICapabilityStore } from "@/stores/ai-capability";
import type { ProviderCardState } from "./types";

/**
 * Provider 管理：抽屉状态、配置保存、连通性测试、模型刷新
 */
export function useProviderManagement() {
  const aiStore = useAICapabilityStore();

  const isDrawerOpen = ref(false);
  const activeProviderId = ref<string | null>(null);
  const isTestingProvider = ref(false);
  const isRefreshingModels = ref(false);
  const isSavingProvider = ref(false);

  const providerCardStates = computed<ProviderCardState[]>(() => {
    return aiStore.providerCatalog.map(p => ({
      ...p,
      health: aiStore.providerHealth[p.provider] || null,
      models: aiStore.modelCatalogByProvider[p.provider] || [],
      loadingModels: false
    }));
  });

  const activeProvider = computed(() => {
    if (!activeProviderId.value) return null;
    return providerCardStates.value.find(p => p.provider === activeProviderId.value) || null;
  });

  function openProviderConfig(id: string) {
    activeProviderId.value = id;
    isDrawerOpen.value = true;
    if (!aiStore.modelCatalogByProvider[id]) {
      void aiStore.loadProviderModels(id);
    }
  }

  async function handleQuickTest(id: string) {
    activeProviderId.value = id;
    isTestingProvider.value = true;
    await aiStore.checkProvider(id);
    isTestingProvider.value = false;
  }

  async function handleProviderTest(modelId?: string) {
    if (!activeProviderId.value) return;
    isTestingProvider.value = true;
    await aiStore.checkProvider(activeProviderId.value, modelId);
    isTestingProvider.value = false;
  }

  async function saveProviderConfig(data: { apiKey: string; baseUrl: string }) {
    if (!activeProviderId.value) return;
    isSavingProvider.value = true;
    await aiStore.saveProviderSecret(activeProviderId.value, data);
    isSavingProvider.value = false;
    isDrawerOpen.value = false;
  }

  async function refreshProviderModels() {
    if (!activeProviderId.value) return;
    isRefreshingModels.value = true;
    if (activeProvider.value?.supportsModelDiscovery) {
      await aiStore.refreshProviderModels(activeProviderId.value);
    } else {
      await aiStore.loadProviderModels(activeProviderId.value);
    }
    isRefreshingModels.value = false;
  }

  async function loadModelsForProvider(providerId: string) {
    await aiStore.loadProviderModels(providerId);
  }

  return {
    isDrawerOpen,
    activeProviderId,
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
  };
}
