import { IconArchive, IconCopy, IconRestore, IconSparkles, IconX } from "@tabler/icons-react";
import { useState } from "react";
import { aiRecipes } from "../../data/aiCapabilities.js";
import { accountCopyFields, accountExcludedFields, accountStatusMeta } from "../../data/accountManagement.js";
import { AIRecipeSummary } from "../ai-recipe/AIRecipeSummary.jsx";
import { ReadinessIndicators } from "./ReadinessIndicators.jsx";

export function AccountDetailDrawer({ account, onArchive, onClose, onCopy, onRestore, onUpdateRecipe }) {
  const [editingRecipe, setEditingRecipe] = useState(false);
  const [recipeId, setRecipeId] = useState(account?.recipe?.id || aiRecipes[0].id);
  if (!account) return null;
  const meta = accountStatusMeta[account.status];
  const selectedRecipe = aiRecipes.find((recipe) => recipe.id === recipeId);
  const nextRecipe = selectedRecipe ? {
    id: selectedRecipe.id,
    name: selectedRecipe.name,
    script: "GPT-5.4 mini",
    visual: selectedRecipe.id === "recipe-image" ? "Flux 参考图" : "Flux 快速图",
    video: selectedRecipe.id === "recipe-image" ? "Wan I2V" : "Seedance Lite",
    voice: selectedRecipe.id === "recipe-calm" ? "Calm EN" : "清亮中性",
    ratio: "9:16",
    inheritance: "账号覆盖 1 项",
  } : account.recipe;
  return (
    <aside className="detail-panel account-detail" aria-label="账号详情">
      <div className="detail-panel__header"><div><span>账号详情 · {meta.label}</span><h2>{account.name}</h2></div><button className="icon-button" aria-label="关闭详情" onClick={onClose} type="button"><IconX size={18} /></button></div>
      <div className="detail-panel__body">
        <section className="account-detail__identity"><p>{account.positioning}</p><ReadinessIndicators readiness={account.readiness} /></section>
        <section className="detail-section"><h3>连接与工作区</h3><dl className="compact-definition"><div><dt>目录</dt><dd>{account.connection.workspace || "未配置"}</dd></div><div><dt>浏览器</dt><dd>{account.connection.browser || "未检查"}</dd></div><div><dt>执行环境</dt><dd>{account.connection.environment || "未检查"}</dd></div></dl></section>
        <section className="detail-section"><div className="section-title-row"><h3>AI 创作档案</h3><button className="text-action" onClick={() => setEditingRecipe((current) => !current)} type="button"><IconSparkles size={15} />{editingRecipe ? "收起" : "编辑配方"}</button></div><AIRecipeSummary recipe={editingRecipe ? nextRecipe : account.recipe} />
          {editingRecipe ? <div className="recipe-editor"><label className="field"><span>账号 Recipe</span><select value={recipeId} onChange={(event) => setRecipeId(event.target.value)}>{aiRecipes.map((recipe) => <option disabled={recipe.providerHealth === "error"} key={recipe.id} value={recipe.id}>{recipe.name}</option>)}</select></label><button className="primary-button" onClick={() => { onUpdateRecipe(account.id, nextRecipe); setEditingRecipe(false); }} type="button">保存账号覆盖</button><button className="ghost-button" onClick={() => setRecipeId(aiRecipes[0].id)} type="button">恢复系统默认</button></div> : null}
        </section>
        <details className="advanced-options"><summary>复制与归档边界</summary><div className="copy-boundaries"><span><strong>会复制</strong>{accountCopyFields.join("、")}</span><span><strong>不会复制</strong>{accountExcludedFields.join("、")}</span></div></details>
      </div>
      <div className="detail-panel__footer account-detail__actions"><button className="secondary-button" onClick={() => onCopy(account.id)} type="button"><IconCopy size={16} />复制配置</button>{account.status === "archived" ? <button className="primary-button" onClick={() => onRestore(account.id)} type="button"><IconRestore size={16} />恢复并检查</button> : <button className="ghost-button danger-action" onClick={() => onArchive(account.id)} type="button"><IconArchive size={16} />归档账号</button>}</div>
    </aside>
  );
}
