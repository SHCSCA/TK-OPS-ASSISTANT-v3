import { IconRefresh, IconVideo } from "@tabler/icons-react";

export function StoryboardSceneDetail({ creative, scene }) {
  return <div className="detail-stack"><div className="scene-detail-visual"><IconVideo size={26} /><strong>镜头 {String(scene.order).padStart(2, "0")}</strong><small>{scene.duration} · 演示规划</small></div>{scene.error ? <div className="detail-alert detail-alert--danger"><strong>局部异常</strong><p>{scene.error}</p></div> : null}<section className="detail-section"><h3>画面</h3><p>{scene.shot}</p></section><section className="detail-section"><h3>旁白</h3><p>{scene.narration}</p></section><button className="primary-button" disabled={scene.status === "running"} onClick={() => creative.retryScene(scene.id)} type="button"><IconRefresh size={16} />{scene.status === "failed" ? "仅重试此镜头" : "重新生成此镜头"}</button></div>;
}
