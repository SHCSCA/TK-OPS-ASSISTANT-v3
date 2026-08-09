import { useState } from "react";
import { PageSection } from "../PageSection.jsx";
import { AICapabilityTabs } from "./AICapabilityTabs.jsx";
import { AIReadinessSummary } from "./AIReadinessSummary.jsx";
import { CapabilityRouteTable } from "./CapabilityRouteTable.jsx";
import { ModelCapabilityDetail } from "./ModelCapabilityDetail.jsx";
import { ModelProfileTable } from "./ModelProfileTable.jsx";
import { PromptProfileEditor } from "./PromptProfileEditor.jsx";
import { PromptProfileTable } from "./PromptProfileTable.jsx";
import { PromptUnsavedDialog } from "./PromptUnsavedDialog.jsx";
import { ProviderDetailDrawer } from "./ProviderDetailDrawer.jsx";
import { ProviderList } from "./ProviderList.jsx";
import { ProviderWizard } from "./ProviderWizard.jsx";

export function AICapabilitiesCenter({ state }) {
  const [tab, setTab] = useState("providers");
  const ai = state.aiSettings;
  const selectedModelProvider = ai.selectedModel ? ai.providers.find((provider) => provider.id === ai.selectedModel.providerProfileId) : null;
  function changeTab(nextTab) {
    ai.setSelectedProviderId(null);
    ai.setSelectedModelId(null);
    setTab(nextTab);
  }
  return <div className="page-stack ai-capabilities-page"><AIReadinessSummary onAddProvider={ai.openProviderWizard} providerCount={ai.providers.length} readyCount={ai.readyRouteCount} routeCount={ai.routes.length} /><AICapabilityTabs activeTab={tab} onChange={changeTab} />{tab === "providers" ? <ProviderPanel ai={ai} /> : null}{tab === "models" ? <div className="page-stack"><PageSection meta="模型声明不等于当前适配器已支持能力" title="模型 Profile"><ModelProfileTable models={ai.models} onOpen={ai.setSelectedModelId} onToggle={ai.toggleModel} providers={ai.providers} /></PageSection><PageSection meta="系统默认 → 账号 Recipe → 本批次覆盖" title="业务能力路由"><CapabilityRouteTable models={ai.models} onUpdate={ai.updateRoute} prompts={ai.prompts} routes={ai.routes} routeStatuses={ai.routeStatuses} /></PageSection></div> : null}{tab === "prompts" ? <div className="prompt-workspace"><PromptProfileTable onCreate={ai.createPrompt} onSelect={ai.requestPromptSelection} prompts={ai.prompts} selectedPromptId={ai.selectedPromptId} /><PromptProfileEditor dirty={ai.promptDirty} draft={ai.promptDraft} onSave={ai.savePromptVersion} onUpdate={ai.updatePromptDraft} templates={ai.templates} /></div> : null}<div className="system-scope-note"><strong>配置继承</strong><span>系统 Provider、模型、路由与 Prompt → 账号 AI Recipe → 本批次覆盖</span></div><ProviderDetailDrawer models={ai.models} onClose={() => ai.setSelectedProviderId(null)} onTest={ai.testProvider} provider={ai.selectedProvider} testing={ai.testingProviderId === ai.selectedProviderId} /><ModelCapabilityDetail model={ai.selectedModel} onClose={() => ai.setSelectedModelId(null)} provider={selectedModelProvider} /><ProviderWizard notify={state.notify} onClose={ai.closeProviderWizard} onSave={ai.saveProvider} open={ai.providerWizardOpen} providers={ai.providers} /><PromptUnsavedDialog onResolve={ai.resolvePromptGuard} open={ai.promptGuardOpen} /></div>;
}

function ProviderPanel({ ai }) {
  return <PageSection meta="系统级连接与安全凭据引用；账号只选择 Recipe" title="Provider Profile"><ProviderList onOpen={ai.setSelectedProviderId} onTest={ai.testProvider} providers={ai.providers} testingProviderId={ai.testingProviderId} /></PageSection>;
}
