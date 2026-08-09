export function CapabilityRouteTable({ models, prompts, routes, routeStatuses, onUpdate }) {
  const enabledModels = models.filter((model) => model.enabled);
  return <div className="route-table"><div className="route-table__head"><span>业务能力</span><span>主模型</span><span>回退模型</span><span>Prompt</span><span>状态</span></div>{routes.map((route) => {
    const status = routeStatuses[route.id];
    return <div className="route-table__row" key={route.id}><strong>{route.label}</strong><RouteSelect ariaLabel={`${route.label}主模型`} items={enabledModels} labelKey="displayName" onChange={(value) => onUpdate(route.id, "primaryModelProfileId", value)} value={route.primaryModelProfileId} /><RouteSelect ariaLabel={`${route.label}回退模型`} items={enabledModels} labelKey="displayName" onChange={(value) => onUpdate(route.id, "fallbackModelProfileId", value)} value={route.fallbackModelProfileId} /><RouteSelect ariaLabel={`${route.label} Prompt`} items={prompts} labelKey="name" onChange={(value) => onUpdate(route.id, "promptProfileId", value)} value={route.promptProfileId} /><span className={status.ready ? "route-state is-ready" : "route-state is-warning"}><i />{status.reason}</span></div>;
  })}</div>;
}

function RouteSelect({ ariaLabel, items, labelKey, onChange, value }) {
  return <select aria-label={ariaLabel} onChange={(event) => onChange(event.target.value)} value={value || ""}><option value="">未配置</option>{items.map((item) => <option key={item.id} value={item.id}>{item[labelKey]}</option>)}</select>;
}
