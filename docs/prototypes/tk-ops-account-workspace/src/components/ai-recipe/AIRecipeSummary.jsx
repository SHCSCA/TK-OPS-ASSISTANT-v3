import { IconMicrophone, IconMovie, IconPhoto, IconSparkles } from "@tabler/icons-react";

export function AIRecipeSummary({ recipe }) {
  if (!recipe) return <div className="recipe-empty"><strong>尚未选择 AI 创作档案</strong><small>选择系统可用 Recipe 后才能进入批量生成。</small></div>;
  return (
    <div className="recipe-summary">
      <div className="recipe-summary__head"><span><IconSparkles size={17} /><strong>{recipe.name}</strong></span><small>{recipe.inheritance || "系统默认"}</small></div>
      <div className="recipe-summary__grid">
        <span><small>脚本</small><strong>{recipe.script}</strong></span>
        <span><small>视觉</small><strong><IconPhoto size={14} />{recipe.visual}</strong></span>
        <span><small>视频</small><strong><IconMovie size={14} />{recipe.video}</strong></span>
        <span><small>声音</small><strong><IconMicrophone size={14} />{recipe.voice}</strong></span>
      </div>
    </div>
  );
}
