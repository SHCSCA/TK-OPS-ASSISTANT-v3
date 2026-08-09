import { IconCheck, IconCircleX, IconDeviceDesktopCheck, IconRocket, IconShieldCheck } from "@tabler/icons-react";
import { PageSection } from "../components/PageSection.jsx";
import { PageEmptyState } from "../components/empty-states/PageEmptyState.jsx";
import { resolvePageEmptyState } from "../utils/resolvePageEmptyState.js";

const statusLabels = { blocked: "预检阻断", preflight: "等待预检", ready: "可以发布" };

export function Publishing({ state }) {
  const emptyState = resolvePageEmptyState("publishing", state.dataScenario, state.workspace.publishing.length > 0);
  if (emptyState) return <div className="page-enter"><PageEmptyState definition={emptyState} onAction={() => state.navigate("production")} /></div>;
  return (
    <div className="page-stack page-enter">
      <section className="binding-strip"><span><IconDeviceDesktopCheck size={20} /><strong>{state.workspace.account.name}</strong><small>{state.workspace.publishing[0]?.binding || "未绑定工作区"}</small></span><span className="status-pill status-pill--ready"><IconCheck size={14} />演示绑定正常</span></section>
      <PageSection title="发布预检" meta="账号、素材、字幕与执行环境必须全部通过">
        <div className="preflight-grid"><span><IconShieldCheck />账号授权<small>演示通过</small></span><span><IconCheck />成片文件<small>已就绪</small></span><span><IconCheck />字幕安全区<small>已检查</small></span><span><IconDeviceDesktopCheck />执行环境<small>已连接</small></span></div>
      </PageSection>
      <PageSection title="待发布内容" meta="演示状态，不代表 TikTok 真实回执">
        <div className="publish-list">
          {state.workspace.publishing.map((item) => (
            <article className="publish-row" key={item.id}>
              <span className={`publish-status-icon ${item.status === "blocked" ? "is-danger" : ""}`}>{item.status === "blocked" ? <IconCircleX size={19} /> : <IconRocket size={19} />}</span>
              <span><strong>{item.title}</strong><small>{item.schedule} · {item.binding}</small></span>
              <span className={`status-pill status-pill--${item.status === "blocked" ? "danger" : item.status === "ready" ? "ready" : "warning"}`}>{statusLabels[item.status]}</span>
              <button className="text-action" onClick={() => state.notify(item.status === "blocked" ? "已打开阻断修复" : "预检任务已开始", "info")} type="button">{item.status === "blocked" ? "修复" : "预检"}</button>
            </article>
          ))}
        </div>
      </PageSection>
    </div>
  );
}
