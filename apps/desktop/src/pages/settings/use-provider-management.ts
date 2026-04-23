import { computed, ref } from "vue";
import { useAIStore } from "@/stores/ai-capability";
import { useConfigBusStore } from "@/stores/config-bus";
import type { ProviderCardState } from "./types";

/**
 * Provider 管理：抽屉状态、配置保存、连通性测试、模型刷新
 */
export function useProviderManagement() {
  const aiStore = useAIStore();
  const configBusStore = useConfigBusStore();

  const isDrawerOpen = ref(false);
  const activeProviderId = ref<string | null>(null);
  const isTestingProvider = ref(false);
  const isRefreshingModels = ref(false);
  const isSavingProvider = ref(false);

  const providerCardStates = computed<ProviderCardState[]>(() => {
    return aiStore.providerCatalog.map(p => ({
      ...p,
      // 这里的 health 是指最近一次连通性测试的详细结果
      health: configBusStore.providerReadiness[p.provider] || null,
      models: aiStore.modelCatalogByProvider[p.provider] || [],
      loadingModels: false,
      readiness: configBusStore.providerReadiness[p.provider] || null
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
       void aiStore.loadModelsForProvider(id);
    }
  }

  async function handleQuickTest(id: string) {
    activeProviderId.value = id;
    isTestingProvider.value = true;
    try {
      await aiStore.checkAIProviderHealth(id);
      // 刷新全局 Readiness 状态
      await configBusStore.fetchProviderReadinessSilently();
    } finally {
      isTestingProvider.value = false;
    }
  }

  async function handleProviderTest(modelId?: string) {
    if (!activeProviderId.value) return;
    isTestingProvider.value = true;
    try {
      // 调用真实 store 链路进行健康检查
      await aiStore.checkAIProviderHealth(activeProviderId.value, modelId ? { model: modelId } : {});
      // 成功后静默刷新 Readiness 摘要
      await configBusStore.fetchProviderReadinessSilently();
    } finally {
      isTestingProvider.value = false;
    }
  }

  async function saveProviderConfig(data: { apiKey: string; baseUrl: string }) {
    if (!activeProviderId.value) return;
    isSavingProvider.value = true;
    try {
       await aiStore.saveProviderSecret(activeProviderId.value, data);
       isDrawerOpen.value = false;
    } finally {
       isSavingProvider.value = false;
    }
  }

  async function refreshProviderModels() {
    if (!activeProviderId.value) return;
    isRefreshingModels.value = true;
    try {
      await aiStore.refreshProviderModels(activeProviderId.value);
    } finally {
      isRefreshingModels.value = false;
    }
  }

  async function loadModelsForProvider(providerId: string) {
    await aiStore.loadModelsForProvider(providerId);
  }

  async function saveProviderModel(modelId: string, capabilityKinds: string[]) {
    if (!activeProviderId.value) return;
    isSavingProvider.value = true;
    try {
      await aiStore.saveProviderModel(activeProviderId.value, modelId, { 
        displayName: modelId, 
        capabilityKinds 
      });
    } finally {
      isSavingProvider.value = false;
    }
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
    loadModelsForProvider,
    saveProviderModel
  };
}
