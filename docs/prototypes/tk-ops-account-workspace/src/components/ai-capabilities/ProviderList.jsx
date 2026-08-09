import { IconBox, IconCloud, IconServer, IconTestPipe } from "@tabler/icons-react";

const adapterIcons = { ComfyUI: IconServer, RunningHub: IconCloud, "直接 API": IconBox };
const healthLabels = { error: "不可用", ready: "健康", untested: "未测试", warning: "需检查" };

export function ProviderList({ providers, onOpen, onTest, testingProviderId }) {
  return <div className="provider-list">{providers.map((provider) => {
    const Icon = adapterIcons[provider.adapter] || IconBox;
    return <article className="provider-row" key={provider.id}><span className="provider-icon"><Icon size={19} /></span><button className="provider-copy" onClick={() => onOpen(provider.id)} type="button"><strong>{provider.name}</strong><small>{provider.adapter} · {provider.capabilities.join(" / ")}</small></button><span className={`status-pill status-pill--${provider.health === "ready" ? "ready" : provider.health === "error" ? "danger" : "warning"}`}>{healthLabels[provider.health] || "未测试"}</span><span className="provider-model-count">{provider.modelIds.length} 个模型</span><button className="text-action" disabled={testingProviderId === provider.id} onClick={() => onTest(provider.id)} type="button"><IconTestPipe size={15} />{testingProviderId === provider.id ? "测试中" : "测试连接"}</button></article>;
  })}</div>;
}
