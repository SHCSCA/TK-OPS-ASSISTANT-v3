import { aiRecipes } from "../../data/aiCapabilities.js";
import { normalizeModelParams } from "./batchWizardHelpers.js";
import { getSourceLabel } from "./BatchSourceStep.jsx";

export function BatchRecipeStep({ form, recipe, recipeContext, update }) {
  const schema = recipeContext.model?.parameterSchema || {};
  const params = normalizeModelParams(recipeContext.model, form.modelParams);
  function chooseRecipe(recipeId) {
    update("recipeId", recipeId);
    update("modelParams", {});
  }
  function updateParam(field, value) {
    update("modelParams", { ...params, [field]: value });
  }
  return <div className="wizard-stack"><div className="recipe-options">{aiRecipes.map((item) => <button className={form.recipeId === item.id ? "is-active" : ""} key={item.id} onClick={() => chooseRecipe(item.id)} type="button"><strong>{item.name}</strong><small>{item.summary}</small></button>)}</div><div className="recipe-inline-summary"><span><small>输入模式</small><strong>{getSourceLabel(form.mode)}</strong></span><span><small>视频模型</small><strong>{recipeContext.model?.displayName || "未配置"}</strong></span><span><small>路由状态</small><strong className={recipeContext.status.ready ? "is-ready" : "is-warning"}>{recipeContext.status.reason}</strong></span></div><details className="advanced-options" open><summary>模型参数</summary><div className="model-param-grid"><ParamSelect label="时长" onChange={(value) => updateParam("duration", value)} options={schema.durations} value={params.duration} /><ParamSelect label="画面比例" onChange={(value) => updateParam("ratio", value)} options={schema.ratios} value={params.ratio} /><ParamSelect label="分辨率" onChange={(value) => updateParam("resolution", value)} options={schema.resolutions} value={params.resolution} /></div><p>{recipe.name} 的参数来自已验证模型契约；无契约时只显示自动值。</p></details></div>;
}

function ParamSelect({ label, onChange, options, value }) {
  const values = options?.length ? options : [value];
  return <label className="field">{label}<select onChange={(event) => onChange(event.target.value)} value={value}>{values.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>;
}
