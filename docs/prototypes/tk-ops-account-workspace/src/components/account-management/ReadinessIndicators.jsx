import { IconBrain, IconDatabase, IconLink } from "@tabler/icons-react";

const labels = {
  ai: { Icon: IconBrain, text: "AI" },
  connection: { Icon: IconLink, text: "连接" },
  knowledge: { Icon: IconDatabase, text: "知识" },
};

export function ReadinessIndicators({ readiness }) {
  return (
    <span className="readiness-indicators" aria-label="账号就绪状态">
      {["connection", "knowledge", "ai"].map((key) => {
        const { Icon, text } = labels[key];
        const state = readiness[key] || "idle";
        return <span className={`readiness-item readiness-item--${state}`} data-tooltip={`${text}：${state === "ready" ? "就绪" : state === "warning" ? "需检查" : state === "error" ? "不可用" : "未配置"}`} key={key}><Icon size={15} /><small>{text}</small></span>;
      })}
    </span>
  );
}
