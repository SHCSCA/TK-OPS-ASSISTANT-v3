import { IconAlertTriangle, IconCheck, IconLoader2, IconVideo } from "@tabler/icons-react";

const statusIcon = { ready: IconCheck, failed: IconAlertTriangle, running: IconLoader2 };

export function StoryboardSceneList({ creative, onOpenScene }) {
  const board = creative.selectedStoryboard;
  if (!board) return <div className="storyboard-empty"><IconVideo size={25} /><strong>还没有分镜</strong><span>采用脚本后生成第一版镜头规划。</span><button className="primary-button" onClick={() => creative.generateStoryboard()} type="button">AI 生成分镜</button></div>;
  return <div className="scene-list">{board.scenes.map((scene) => { const StatusIcon = statusIcon[scene.status] || IconVideo; return <button className={`scene-row ${scene.status === "failed" ? "is-failed" : ""}`} key={scene.id} onClick={() => { creative.selectScene(scene.id); onOpenScene(scene); }} type="button"><span className="scene-order">{String(scene.order).padStart(2, "0")}</span><span className="scene-copy"><strong>{scene.title}</strong><small>{scene.shot}</small></span><span className="scene-time">{scene.duration}</span><span className={`scene-state scene-state--${scene.status}`}><StatusIcon className={scene.status === "running" ? "spin" : ""} size={15} />{scene.status === "ready" ? "就绪" : scene.status === "failed" ? "失败" : "重试中"}</span></button>; })}</div>;
}
