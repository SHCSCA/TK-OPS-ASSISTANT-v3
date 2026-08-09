export function PageSection({ title, meta, action, children, className = "" }) {
  return (
    <section className={`page-section ${className}`}>
      <div className="page-section__header">
        <div><h2>{title}</h2>{meta ? <p>{meta}</p> : null}</div>
        {action}
      </div>
      {children}
    </section>
  );
}
