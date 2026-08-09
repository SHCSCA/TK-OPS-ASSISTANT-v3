import { IconArrowLeft, IconArrowRight, IconCheck, IconLoader2, IconPlus, IconTestPipe, IconX } from "@tabler/icons-react";
import { useState } from "react";
import { prototypeConfig } from "../../config/prototypeConfig.js";
import { prototypeLogger } from "../../utils/logger.js";
import { applyAdapterDefaults, createProviderDraft, discoverDemoModels, normalizeDiscoveredModels, validateProviderStep } from "./providerWizardHelpers.js";

const stepLabels = ["连接类型", "地址与凭据", "运行参数", "发现模型", "测试并保存"];

export function ProviderWizard({ onClose, onSave, open, notify, providers }) {
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState(createProviderDraft);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [tested, setTested] = useState(false);
  const [confirmClose, setConfirmClose] = useState(false);
  const [manualModel, setManualModel] = useState({ displayName: "", modelId: "" });
  if (!open) return null;

  function update(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
    setError("");
    setTested(false);
  }

  function close() {
    if (step > 0 || draft.discoveredModels.length) {
      setConfirmClose(true);
      return;
    }
    resetAndClose();
  }

  function resetAndClose() {
    setStep(0);
    setDraft(createProviderDraft());
    setBusy("");
    setError("");
    setTested(false);
    setConfirmClose(false);
    setManualModel({ displayName: "", modelId: "" });
    onClose();
  }

  function next() {
    const message = validateProviderStep(step, draft);
    if (message) return setError(message);
    setStep((current) => Math.min(4, current + 1));
  }

  async function discover() {
    setBusy("discover");
    setError("");
    try {
      await new Promise((resolve) => window.setTimeout(resolve, prototypeConfig.ai.modelDiscoveryDelay));
      const models = discoverDemoModels(draft.adapterType);
      setDraft((current) => ({ ...current, discoveredModels: models }));
      notify(`已发现 ${models.length} 个演示模型`, "info");
    } catch (discoverError) {
      prototypeLogger.error("发现模型失败", discoverError, { adapterType: draft.adapterType });
      setError("模型发现失败，请重试");
    } finally {
      setBusy("");
    }
  }

  async function testConnection() {
    setBusy("test");
    setError("");
    try {
      await new Promise((resolve) => window.setTimeout(resolve, prototypeConfig.ai.providerTestDelay));
      if (draft.baseUrl.includes("invalid")) throw new Error("演示地址不可达");
      setTested(true);
      notify("Provider 演示连接测试通过");
    } catch (testError) {
      prototypeLogger.error("Provider 向导连接测试失败", testError, { baseUrl: draft.baseUrl });
      setTested(false);
      setError("连接测试失败，请检查地址或凭据引用");
    } finally {
      setBusy("");
    }
  }

  function addManualModel() {
    const modelId = manualModel.modelId.trim();
    const displayName = manualModel.displayName.trim();
    if (!modelId || !displayName) return setError("请填写模型 ID 和显示名");
    if (draft.discoveredModels.some((model) => model.modelId === modelId)) return setError("当前模型 ID 已存在");
    const model = { modelId, displayName, declaredAbilities: ["text-generation"], adapterAbilities: ["text-generation"], inputModalities: ["文本"], adapterInputModalities: ["文本"], contextLimit: "待验证", parameterSchema: { temperature: "0–2" } };
    setDraft((current) => ({ ...current, discoveredModels: [...current.discoveredModels, model] }));
    setManualModel({ displayName: "", modelId: "" });
    setError("");
    notify("手动模型已加入待保存列表", "info");
  }

  function save() {
    if (!tested) return setError("请先完成连接测试");
    if (providers.some((item) => item.name.trim().toLowerCase() === draft.name.trim().toLowerCase())) return setError("Provider 名称已存在，请返回修改");
    const providerId = `provider-${Date.now()}`;
    const adapter = prototypeConfig.ai.adapterTypes.find((item) => item.id === draft.adapterType);
    const models = normalizeDiscoveredModels(providerId, draft.discoveredModels);
    const provider = {
      id: providerId,
      name: draft.name,
      adapter: adapter?.label || draft.adapterType,
      adapterType: draft.adapterType,
      baseUrl: draft.baseUrl,
      capabilities: [...new Set(models.flatMap((model) => model.adapterAbilities))],
      concurrency: Number(draft.concurrency),
      credentialRef: draft.credentialRef,
      demo: true,
      health: "ready",
      lastTestedAt: "刚刚",
      logId: `DEMO-AI-${Date.now()}`,
      modelIds: [],
      timeoutSeconds: Number(draft.timeoutSeconds),
    };
    if (onSave({ provider, models })) resetAndClose();
  }

  return <div className="modal-backdrop" role="presentation"><section aria-labelledby="provider-wizard-title" aria-modal="true" className="batch-dialog provider-wizard" role="dialog"><header className="dialog-header"><div><span className="dialog-eyebrow">AI 配置</span><h2 id="provider-wizard-title">添加 Provider</h2></div><button aria-label="关闭向导" className="icon-button" onClick={close} type="button"><IconX size={18} /></button></header><div className="provider-wizard__steps">{stepLabels.map((label, index) => <span className={index === step ? "is-active" : index < step ? "is-done" : ""} key={label}><i>{index < step ? <IconCheck size={12} /> : index + 1}</i>{label}</span>)}</div><div className="provider-wizard__body">{step === 0 ? <AdapterStep draft={draft} onChange={(value) => setDraft((current) => applyAdapterDefaults(current, value))} /> : null}{step === 1 ? <ConnectionStep draft={draft} update={update} /> : null}{step === 2 ? <RuntimeStep draft={draft} update={update} /> : null}{step === 3 ? <DiscoveryStep busy={busy} draft={draft} manualModel={manualModel} onAddManual={addManualModel} onDiscover={discover} setManualModel={setManualModel} /> : null}{step === 4 ? <ReviewStep busy={busy} draft={draft} onTest={testConnection} tested={tested} /> : null}{error ? <p className="wizard-error" role="alert">{error}</p> : null}</div><footer className="dialog-actions"><button className="ghost-button" disabled={step === 0 || Boolean(busy)} onClick={() => setStep((current) => current - 1)} type="button"><IconArrowLeft size={16} />上一步</button>{step < 4 ? <button className="primary-button" disabled={Boolean(busy)} onClick={next} type="button">下一步<IconArrowRight size={16} /></button> : <button className="primary-button" disabled={Boolean(busy) || !tested} onClick={save} type="button"><IconPlus size={16} />保存 Provider</button>}</footer></section>{confirmClose ? <section aria-label="放弃 Provider 配置" className="wizard-confirm"><strong>放弃当前配置？</strong><span>未保存的连接和模型设置会丢失。</span><div><button className="ghost-button" onClick={() => setConfirmClose(false)} type="button">继续编辑</button><button className="primary-button" onClick={resetAndClose} type="button">放弃</button></div></section> : null}</div>;
}

function AdapterStep({ draft, onChange }) {
  return <div className="adapter-grid">{prototypeConfig.ai.adapterTypes.map((adapter) => <button className={draft.adapterType === adapter.id ? "is-active" : ""} key={adapter.id} onClick={() => onChange(adapter.id)} type="button"><strong>{adapter.label}</strong><small>{adapter.id === "comfyui" ? "本地工作流" : adapter.id === "runninghub" ? "远程工作流" : "标准兼容接口"}</small></button>)}</div>;
}

function ConnectionStep({ draft, update }) {
  return <div className="wizard-fields"><label className="field">名称<input onChange={(event) => update("name", event.target.value)} value={draft.name} /></label><label className="field field--wide">Base URL<input onChange={(event) => update("baseUrl", event.target.value)} value={draft.baseUrl} /></label><label className="field field--wide">凭据安全引用<input onChange={(event) => update("credentialRef", event.target.value)} value={draft.credentialRef} /></label><p className="field-hint">原型只保存凭据引用，不采集真实密钥。</p></div>;
}

function RuntimeStep({ draft, update }) {
  return <div className="wizard-fields"><label className="field">最大并发<input min="1" onChange={(event) => update("concurrency", event.target.value)} type="number" value={draft.concurrency} /></label><label className="field">超时（秒）<input min="1" onChange={(event) => update("timeoutSeconds", event.target.value)} type="number" value={draft.timeoutSeconds} /></label><p className="field-hint">长任务必须有超时、失败反馈与重试路径；参数统一进入配置总线。</p></div>;
}

function DiscoveryStep({ busy, draft, manualModel, onAddManual, onDiscover, setManualModel }) {
  function updateManual(field, value) {
    setManualModel((current) => ({ ...current, [field]: value }));
  }
  return <div className="discovery-panel"><div><strong>发现可用模型</strong><small>能力声明与当前适配器可用能力分开展示。</small></div><button className="secondary-button" disabled={busy === "discover"} onClick={onDiscover} type="button">{busy === "discover" ? <IconLoader2 className="spin" size={16} /> : <IconTestPipe size={16} />}{busy === "discover" ? "发现中" : "开始发现"}</button><div className="manual-model-row"><label className="field">模型 ID<input onChange={(event) => updateManual("modelId", event.target.value)} placeholder="例如 model-v1" value={manualModel.modelId} /></label><label className="field">显示名<input onChange={(event) => updateManual("displayName", event.target.value)} placeholder="用于界面识别" value={manualModel.displayName} /></label><button className="secondary-button" onClick={onAddManual} type="button">手动添加</button></div>{draft.discoveredModels.map((model) => <article key={model.modelId}><strong>{model.displayName}</strong><span>{model.adapterAbilities.join(" · ")}</span></article>)}</div>;
}

function ReviewStep({ busy, draft, onTest, tested }) {
  return <div className="provider-review"><dl className="compact-definition"><div><dt>Provider</dt><dd>{draft.name}</dd></div><div><dt>地址</dt><dd>{draft.baseUrl}</dd></div><div><dt>模型</dt><dd>{draft.discoveredModels.length} 个</dd></div><div><dt>运行</dt><dd>并发 {draft.concurrency} · {draft.timeoutSeconds} 秒</dd></div></dl><button className={tested ? "secondary-button is-success" : "secondary-button"} disabled={busy === "test"} onClick={onTest} type="button">{busy === "test" ? <IconLoader2 className="spin" size={16} /> : tested ? <IconCheck size={16} /> : <IconTestPipe size={16} />}{busy === "test" ? "测试中" : tested ? "连接通过" : "测试连接"}</button></div>;
}
