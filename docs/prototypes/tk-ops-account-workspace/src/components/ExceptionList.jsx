import { IconAlertTriangle, IconCircleCheck, IconCircleX, IconChevronRight } from "@tabler/icons-react";

export function ExceptionList({ exceptions, onOpen, onRetry }) {
  return (
    <section className="section-block exception-section">
      <div className="section-heading">
        <h2>待处理异常</h2>
        <span>{exceptions.length ? `${exceptions.length} 项需要确认` : "当前没有阻断项"}</span>
      </div>
      {exceptions.length ? (
        <div className="exception-list">
          {exceptions.map((item) => {
            const Icon = item.tone === "danger" ? IconCircleX : IconAlertTriangle;
            return (
              <article className={`exception-row exception-row--${item.tone}`} key={item.id}>
                <button className="exception-row__main" onClick={() => onOpen({ type: "exception", data: item })} type="button">
                  <span className="exception-row__icon"><Icon size={18} /></span>
                  <span><strong>{item.title}</strong><small>{item.detail}</small></span>
                </button>
                <button className="secondary-button" onClick={() => onRetry(item.id)} type="button">
                  {item.action}<IconChevronRight size={15} />
                </button>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="quiet-success"><IconCircleCheck size={18} />当前账号没有待处理异常</div>
      )}
    </section>
  );
}
