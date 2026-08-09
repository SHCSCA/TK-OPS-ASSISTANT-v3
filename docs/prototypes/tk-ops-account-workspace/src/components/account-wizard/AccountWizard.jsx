import { IconCheck, IconChevronLeft, IconChevronRight, IconLoader2, IconX } from "@tabler/icons-react";
import { useMemo, useState } from "react";
import { aiRecipes } from "../../data/aiCapabilities.js";
import { prototypeConfig } from "../../config/prototypeConfig.js";
import { AIRecipeSummary } from "../ai-recipe/AIRecipeSummary.jsx";

const steps = ["基础身份", "真实连接", "定位", "知识库", "AI 档案", "健康检查"];

function recipeFromPreset(recipe) {
  return {
    id: recipe.id,
    name: recipe.name,
    script: "GPT-5.4 mini",
    visual: recipe.id === "recipe-image" ? "Flux 参考图" : "Flux 快速图",
    video: recipe.id === "recipe-image" ? "Wan I2V" : "Seedance Lite",
    voice: recipe.id === "recipe-calm" ? "Calm EN" : "清亮中性",
    ratio: "9:16",
    inheritance: "系统默认",
  };
}

export function AccountWizard({ open, source, onClose, onComplete, onSaveDraft }) {
  const [step, setStep] = useState(0);
  const [checking, setChecking] = useState(false);
  const [form, setForm] = useState(() => ({
    id: source?.status === "draft" ? source.id : null,
    name: source ? `${source.name} 副本` : "",
    timezone: "Asia/Shanghai",
    language: "中文",
    positioning: source?.positioning || "",
    shortPositioning: source?.shortPositioning || "",
    audience: "想提升内容生产效率的创作者",
    pillars: "工具拆解、效率实验、真实复盘",
    boundaries: "不做收益承诺，不跨账号引用资料",
    connectionState: "idle",
    connection: { workspace: "G:/TK-OPS/new-account", browser: "演示浏览器实例", environment: "本机 Runtime" },
    knowledgeReady: false,
    recipeId: source?.recipe?.id || prototypeConfig.ai.defaultRecipeId,
    recipe: source?.recipe || recipeFromPreset(aiRecipes.find((item) => item.id === prototypeConfig.ai.defaultRecipeId) || aiRecipes[0]),
  }));
  const recipe = useMemo(() => recipeFromPreset(aiRecipes.find((item) => item.id === form.recipeId) || aiRecipes[0]), [form.recipeId]);
  if (!open) return null;

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function runConnectionCheck() {
    setChecking(true);
    update("connectionState", "checking");
    await new Promise((resolve) => window.setTimeout(resolve, prototypeConfig.actionDelay));
    update("connectionState", form.connectionState === "failed" ? "passed" : "failed");
    setChecking(false);
  }

  function next() {
    if (step === 0 && !form.name.trim()) return;
    setStep((current) => Math.min(steps.length - 1, current + 1));
  }

  function complete() {
    onComplete({ ...form, recipe, knowledgeReady: form.knowledgeReady });
  }

  const healthItems = [
    ["基础身份", Boolean(form.name.trim())],
    ["授权与工作区", form.connectionState === "passed"],
    ["知识库初始化", form.knowledgeReady],
    ["AI 配方可用性", Boolean(recipe)],
    ["发布前置条件", form.connectionState === "passed"],
  ];
  const allReady = healthItems.every((item) => item[1]);

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="account-wizard" role="dialog" aria-modal="true" aria-labelledby="account-wizard-title">
        <aside className="wizard-steps"><span className="dialog-eyebrow">添加账号</span><h2 id="account-wizard-title">建立独立工作区</h2>{steps.map((label, index) => <button className={step === index ? "is-active" : index < step ? "is-done" : ""} key={label} onClick={() => index <= step && setStep(index)} type="button"><i>{index < step ? <IconCheck size={13} /> : index + 1}</i><span>{label}</span></button>)}</aside>
        <div className="wizard-main">
          <header className="wizard-header"><div><small>第 {step + 1} / {steps.length} 步</small><h3>{steps[step]}</h3></div><button className="icon-button" aria-label="关闭向导" onClick={onClose} type="button"><IconX size={18} /></button></header>
          <div className="wizard-body">
            {step === 0 ? <div className="wizard-grid"><label className="field field--wide"><span>账号显示名</span><input value={form.name} onChange={(event) => update("name", event.target.value)} placeholder="例如：镜头 A" autoFocus /></label><label className="field"><span>平台</span><select disabled><option>TikTok</option></select></label><label className="field"><span>语言</span><select value={form.language} onChange={(event) => update("language", event.target.value)}><option>中文</option><option>English</option></select></label><label className="field field--wide"><span>时区</span><select value={form.timezone} onChange={(event) => update("timezone", event.target.value)}><option>Asia/Shanghai</option><option>America/Los_Angeles</option></select></label></div> : null}
            {step === 1 ? <div className="wizard-stack"><div className={`connection-check connection-check--${form.connectionState}`}><span><strong>真实对象演示检查</strong><small>不会执行真实 TikTok 授权或设备绑定</small></span><button className="secondary-button" disabled={checking} onClick={runConnectionCheck} type="button">{checking ? <IconLoader2 className="spin" size={16} /> : null}{form.connectionState === "failed" ? "重试检查" : "演示检查"}</button></div><dl className="compact-definition"><div><dt>本地目录</dt><dd>{form.connection.workspace}</dd></div><div><dt>浏览器实例</dt><dd>{form.connection.browser}</dd></div><div><dt>执行环境</dt><dd>{form.connection.environment}</dd></div></dl>{form.connectionState === "failed" ? <div className="inline-alert inline-alert--danger"><strong>演示失败：浏览器授权已过期</strong><small>重新检查后将演示通过状态。</small></div> : form.connectionState === "passed" ? <div className="inline-alert inline-alert--success"><strong>演示检查通过</strong><small>所有连接状态仅用于原型验证。</small></div> : null}</div> : null}
            {step === 2 ? <div className="wizard-grid"><label className="field field--wide"><span>一句话定位</span><input value={form.positioning} onChange={(event) => update("positioning", event.target.value)} placeholder="用一句话描述账号为谁解决什么问题" /></label><label className="field field--wide"><span>目标受众</span><input value={form.audience} onChange={(event) => update("audience", event.target.value)} /></label><label className="field field--wide"><span>内容支柱</span><input value={form.pillars} onChange={(event) => update("pillars", event.target.value)} /></label><label className="field field--wide"><span>表达边界</span><input value={form.boundaries} onChange={(event) => update("boundaries", event.target.value)} /></label></div> : null}
            {step === 3 ? <div className="wizard-stack"><div className="knowledge-scope"><IconCheck size={18} /><span><strong>初始化账号独立知识空间</strong><small>来源、索引和快照不会与其他账号共享。</small></span><button className={`toggle-control ${form.knowledgeReady ? "is-on" : ""}`} aria-pressed={form.knowledgeReady} onClick={() => update("knowledgeReady", !form.knowledgeReady)} type="button"><i /></button></div><div className="source-choice-grid"><button type="button">品牌资料</button><button type="button">本地文档</button><button type="button">参考视频</button><button type="button">历史内容</button></div><p className="setting-hint">原型只演示初始化状态，不声称已生成真实向量索引。</p></div> : null}
            {step === 4 ? <div className="wizard-stack"><div className="recipe-options">{aiRecipes.map((item) => <button className={form.recipeId === item.id ? "is-active" : ""} key={item.id} onClick={() => update("recipeId", item.id)} type="button"><strong>{item.name}</strong><small>{item.summary}</small></button>)}</div><AIRecipeSummary recipe={recipe} /><details className="advanced-options"><summary>高级参数</summary><p>Provider、并发和超时由系统配置总线继承；账号这里只保存配方覆盖。</p></details></div> : null}
            {step === 5 ? <div className="health-check-list">{healthItems.map(([label, ready]) => <span key={label}><i className={ready ? "is-ready" : "is-warning"}>{ready ? <IconCheck size={14} /> : "!"}</i><strong>{label}</strong><small>{ready ? "通过" : "待处理"}</small></span>)}<div className={`inline-alert ${allReady ? "inline-alert--success" : "inline-alert--warning"}`}><strong>{allReady ? "账号可以进入生产" : "账号将保存为未绑定状态"}</strong><small>{allReady ? "创建后可立即切换整个工作区。" : "未通过项不会被伪装为已就绪。"}</small></div></div> : null}
          </div>
          <footer className="wizard-actions"><button className="ghost-button" onClick={() => onSaveDraft({ ...form, recipe })} type="button">保存草稿</button><span /><button className="secondary-button" disabled={step === 0} onClick={() => setStep((current) => Math.max(0, current - 1))} type="button"><IconChevronLeft size={16} />上一步</button>{step < steps.length - 1 ? <button className="primary-button" onClick={next} type="button">下一步<IconChevronRight size={16} /></button> : <button className="primary-button" disabled={!form.name.trim()} onClick={complete} type="button">{allReady ? "创建并切换" : "保存未绑定账号"}</button>}</footer>
        </div>
      </section>
    </div>
  );
}
