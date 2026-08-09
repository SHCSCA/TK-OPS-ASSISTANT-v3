import { IconAlertCircle, IconCircleCheck, IconPackage, IconPlayerPlay } from "@tabler/icons-react";

const stageTone = {
  生成: "ai",
  待发布: "ready",
};

export function BatchTable({ batches, stageFilter, onOpen, onRetry }) {
  const visible = stageFilter ? batches.filter((batch) => batch.stage === stageFilter) : batches;
  return (
    <section className="section-block batches-section">
      <div className="section-heading">
        <h2>当前批次</h2>
        <span>{stageFilter ? `已筛选 · ${stageFilter}` : `${visible.length} 个演示批次`}</span>
      </div>
      <div className="data-table-shell">
        <table className="data-table">
          <thead>
            <tr><th>批次</th><th>阶段</th><th>进度</th><th>更新时间</th><th aria-label="动作" /></tr>
          </thead>
          <tbody>
            {visible.map((batch) => {
              const failed = batch.status === "failed";
              return (
                <tr className={failed ? "is-failed" : ""} key={batch.id}>
                  <td>
                    <button className="batch-name" onClick={() => onOpen({ type: "batch", data: batch })} type="button">
                      <span className={`batch-icon ${failed ? "is-danger" : ""}`}>
                        {failed ? <IconAlertCircle size={17} /> : <IconPackage size={17} />}
                      </span>
                      <span><strong>{batch.name}</strong><small>{batch.items} 条内容</small></span>
                    </button>
                  </td>
                  <td><span className={`status-pill status-pill--${failed ? "danger" : stageTone[batch.stage] || "brand"}`}>{batch.stage}</span></td>
                  <td>
                    <div className="progress-cell">
                      <span className="progress-track"><i style={{ width: `${batch.progress}%` }} /></span>
                      <small>{batch.progress}%</small>
                    </div>
                  </td>
                  <td className="muted-cell">{batch.updated}</td>
                  <td className="action-cell">
                    {failed ? (
                      <button className="text-action text-action--danger" onClick={() => onRetry(batch.id)} type="button">重试</button>
                    ) : (
                      <button className="text-action" onClick={() => onOpen({ type: "batch", data: batch })} type="button">
                        {batch.status === "ready" ? <IconCircleCheck size={15} /> : <IconPlayerPlay size={15} />}
                        {batch.status === "ready" ? "预览" : "查看"}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {visible.length === 0 ? <div className="table-empty">这个阶段还没有批次</div> : null}
      </div>
    </section>
  );
}
