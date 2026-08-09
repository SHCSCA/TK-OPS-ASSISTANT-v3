import { useMemo, useState } from "react";
import { prototypeConfig } from "../../config/prototypeConfig.js";
import { cloneProviderProfiles } from "../../data/aiCapabilities.js";
import { prototypeLogger } from "../../utils/logger.js";

export function useProviderProfilesState(notify) {
  const [providers, setProviders] = useState(cloneProviderProfiles);
  const [selectedProviderId, setSelectedProviderId] = useState(null);
  const [testingProviderId, setTestingProviderId] = useState(null);
  const [providerWizardOpen, setProviderWizardOpen] = useState(false);
  const selectedProvider = useMemo(() => providers.find((provider) => provider.id === selectedProviderId) || null, [providers, selectedProviderId]);

  async function testProvider(providerId) {
    setTestingProviderId(providerId);
    notify("正在执行演示连接测试", "info");
    try {
      await new Promise((resolve) => window.setTimeout(resolve, prototypeConfig.ai.providerTestDelay));
      const nextHealth = providerId === "runninghub" ? "error" : "ready";
      setProviders((current) => current.map((provider) => provider.id === providerId ? { ...provider, health: nextHealth, lastTestedAt: "刚刚" } : provider));
      if (nextHealth === "error") {
        prototypeLogger.error("Provider 演示连接失败", new Error("演示凭据引用无效"), { providerId });
        notify("演示连接失败：凭据引用无效", "danger");
      } else {
        prototypeLogger.info("Provider 演示连接通过", { providerId });
        notify("演示连接测试通过");
      }
    } catch (error) {
      prototypeLogger.error("Provider 连接测试异常", error, { providerId });
      notify("连接测试失败，请查看日志", "danger");
    } finally {
      setTestingProviderId(null);
    }
  }

  function addProvider(provider) {
    try {
      setProviders((current) => [provider, ...current]);
      setSelectedProviderId(provider.id);
      setProviderWizardOpen(false);
      prototypeLogger.info("演示 Provider 已保存", { providerId: provider.id });
      notify("Provider 已保存，请继续检查能力路由");
      return true;
    } catch (error) {
      prototypeLogger.error("保存 Provider 失败", error);
      notify("Provider 保存失败，请重试", "danger");
      return false;
    }
  }

  return {
    addProvider,
    closeProviderWizard: () => setProviderWizardOpen(false),
    openProviderWizard: () => setProviderWizardOpen(true),
    providerWizardOpen,
    providers,
    selectedProvider,
    selectedProviderId,
    setSelectedProviderId,
    testProvider,
    testingProviderId,
  };
}
