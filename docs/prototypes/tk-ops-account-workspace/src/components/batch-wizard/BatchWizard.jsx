import { IconCheck, IconChevronLeft, IconChevronRight, IconLoader2, IconSparkles, IconX } from "@tabler/icons-react";
import { useEffect, useMemo, useState } from "react";
import { prototypeConfig } from "../../config/prototypeConfig.js";
import { aiRecipes } from "../../data/aiCapabilities.js";
import { BatchRecipeStep } from "./BatchRecipeStep.jsx";
import { BatchSourceStep } from "./BatchSourceStep.jsx";
import { createBatchForm, getBatchAssets, getSplitModeLabel, normalizeModelParams, resolveRecipeContext, splitFixedScript, validateBatchSource } from "./batchWizardHelpers.js";

const steps = ["输入来源", "计划与知识", "AI 配方", "执行确认"];

export function BatchWizard({ accountName, accountProfile, aiSettings, onClose, onSubmit, open, workspace }) {
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState(() => createBatchForm(accountProfile?.recipe?.id || prototypeConfig.ai.defaultRecipeId));
  const recipe = useMemo(() => aiRecipes.find((item) => item.id === form.recipeId) || aiRecipes[0], [form.recipeId]);
  const recipeContext = resolveRecipeContext(recipe, aiSettings);
  const assets = getBatchAssets(workspace);
  const scriptSegments = splitFixedScript(form.fixedScript, form.splitMode);
  useEffect(() => {
    if (!open || !recipeContext.model) return;
    setForm((current) => ({ ...current, modelParams: normalizeModelParams(recipeContext.model, current.modelParams) }));
  }, [open, recipeContext.model?.id]);
  if (!open) return null;
  const knowledgeReady = workspace.knowledge.some((item) => item.status === "ready");
  const effectiveCount = form.mode === "script" ? scriptSegments.length : Number(form.count);
  const nodes = [form.mode === "script" ? "固定脚本" : form.mode === "confirmed" ? "已确认内容" : form.mode === "assets" ? "素材分析" : "主题", "脚本", "分镜", "视觉规划", form.useImageToVideo ? "图生视频" : "图片 / 视频", "TTS", "字幕", "合成 / BGM", "预览"];

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setError("");
  }

  function next() {
    if (step === 0) {
      const sourceError = validateBatchSource(form, assets);
      if (sourceError) return setError(sourceError);
    }
    if (step === 1 && !form.name.trim()) return setError("请输入批次名称");
    if (step === 1 && !knowledgeReady) return setError("当前账号没有可用知识快照");
    if (step === 2 && !recipeContext.status.ready) return setError(`当前配方不可执行：${recipeContext.status.reason}`);
    setStep((current) => Math.min(steps.length - 1, current + 1));
  }

  async function submit() {
    setSubmitting(true);
    const created = await onSubmit({ ...form, count: effectiveCount, modelParams: form.modelParams, name: form.name.trim(), recipe: recipe.name, scriptSegments });
    setSubmitting(false);
    if (!created) setError("创建失败，请重试");
  }

  return <div className="modal-backdrop" role="presentation"><section aria-labelledby="batch-wizard-title" aria-modal="true" className="batch-wizard" role="dialog"><header className="dialog-header"><div><span className="dialog-eyebrow">{accountName} · 第 {step + 1} / 4 步</span><h2 id="batch-wizard-title">{steps[step]}</h2></div><button aria-label="关闭" className="icon-button" onClick={onClose} type="button"><IconX size={18} /></button></header><div className="batch-wizard__steps">{steps.map((label, index) => <span className={step === index ? "is-active" : index < step ? "is-done" : ""} key={label}><i>{index < step ? <IconCheck size={12} /> : index + 1}</i>{label}</span>)}</div><div className="batch-wizard__body">{step === 0 ? <BatchSourceStep assets={assets} canImageToVideo={recipe.videoCapability === "image-to-video"} form={form} update={update} /> : null}{step === 1 ? <PlanStep accountName={accountName} effectiveCount={effectiveCount} error={error} form={form} knowledgeReady={knowledgeReady} update={update} workspace={workspace} /> : null}{step === 2 ? <BatchRecipeStep form={form} recipe={recipe} recipeContext={recipeContext} update={update} /> : null}{step === 3 ? <ConfirmStep accountName={accountName} assets={assets} effectiveCount={effectiveCount} error={error} form={form} nodes={nodes} recipe={recipe} recipeContext={recipeContext} /> : null}{step !== 1 && error ? <div className="inline-alert inline-alert--danger"><strong>{error}</strong><small>已保留当前输入，可直接修正。</small></div> : null}</div><footer className="dialog-actions"><button className="ghost-button" onClick={onClose} type="button">取消</button><span /><button className="secondary-button" disabled={step === 0} onClick={() => setStep((current) => Math.max(0, current - 1))} type="button"><IconChevronLeft size={16} />上一步</button>{step < 3 ? <button className="primary-button" onClick={next} type="button">下一步<IconChevronRight size={16} /></button> : <button className="primary-button" disabled={submitting} onClick={submit} type="button">{submitting ? <IconLoader2 className="spin" size={16} /> : <IconSparkles size={16} />}{submitting ? "开始中" : "开始生成"}</button>}</footer></section></div>;
}

function PlanStep({ accountName, effectiveCount, error, form, knowledgeReady, update, workspace }) {
  return <div className="wizard-grid"><label className="field field--wide"><span>批次名称</span><input autoFocus className={error ? "is-error" : ""} onChange={(event) => update("name", event.target.value)} placeholder="例如：本周工具拆解" value={form.name} />{error ? <small className="field-error">{error}</small> : null}</label><label className="field"><span>内容目标</span><select onChange={(event) => update("goal", event.target.value)} value={form.goal}><option>账号定位内容</option><option>知识库补充内容</option><option>热点响应内容</option></select></label><label className="field"><span>生成数量</span><input disabled={form.mode === "script"} max="20" min="1" onChange={(event) => update("count", Number(event.target.value))} type="number" value={effectiveCount} /></label><div className="snapshot-summary field--wide"><span><small>定位版本</small><strong>{workspace.strategy.version}</strong></span><span><small>知识快照</small><strong>{knowledgeReady ? `${accountName} · 演示快照` : "不可用"}</strong></span><span><small>素材范围</small><strong>仅当前账号</strong></span></div></div>;
}

function ConfirmStep({ accountName, assets, effectiveCount, error, form, nodes, recipe, recipeContext }) {
  return <div className="execution-confirm"><div className="confirm-grid"><span><small>账号</small><strong>{accountName}</strong></span><span><small>内容数量</small><strong>{effectiveCount} 条</strong></span><span><small>输入细节</small><strong>{form.mode === "script" ? getSplitModeLabel(form.splitMode) : form.mode === "assets" ? `${form.assetIds.length} 项素材` : "当前账号来源"}</strong></span><span><small>AI Recipe</small><strong>{recipe.name}</strong></span><span><small>视频模型</small><strong>{recipeContext.model?.displayName || "未配置"}</strong></span><span><small>模型参数</small><strong>{Object.values(form.modelParams).filter(Boolean).join(" · ") || "模型默认"}</strong></span></div>{form.mode === "assets" ? <div className="asset-analysis-summary"><strong>视觉规划输入</strong><span>{assets.filter((asset) => form.assetIds.includes(asset.id)).map((asset) => asset.title).join("、")}</span><small>先提取构图、镜头用途与可复用片段，再决定生成或复用。</small></div> : null}<div className="execution-nodes">{nodes.map((node, index) => <span key={`${node}-${index}`}>{node}</span>)}</div>{error ? <div className="inline-alert inline-alert--danger"><strong>{error}</strong><small>保留当前表单，可直接重试。</small></div> : null}</div>;
}
