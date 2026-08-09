import { IconFilter, IconSearch, IconX } from "@tabler/icons-react";
import { useState } from "react";

export function AssetToolbar({ library }) {
  const [filtersOpen, setFiltersOpen] = useState(false);
  const activeFilters = ["purpose", "source", "status"].filter((key) => library.filters[key]);
  return <div className="asset-toolbar"><div className="asset-toolbar__primary"><label className="asset-search"><IconSearch size={16} /><input aria-label="搜索资产" onChange={(event) => library.setFilter("query", event.target.value)} placeholder="搜索内容库" value={library.filters.query} /></label><div className="asset-type-tabs" role="tablist">{library.options.types.map((item) => <button aria-selected={library.filters.type === item.value} className={library.filters.type === item.value ? "is-active" : ""} key={item.value} onClick={() => library.setFilter("type", item.value)} role="tab" type="button">{item.label}</button>)}</div><button className={`secondary-button ${activeFilters.length ? "has-filter" : ""}`} onClick={() => setFiltersOpen((current) => !current)} type="button"><IconFilter size={15} />筛选{activeFilters.length ? ` ${activeFilters.length}` : ""}</button><select aria-label="资产排序" className="asset-sort" onChange={(event) => library.setSort(event.target.value)} value={library.sort}><option value="latest">最近更新</option><option value="name">名称</option><option value="type">类型</option></select></div>{filtersOpen ? <div className="asset-filter-popover"><FilterSelect label="用途" options={library.options.purposes} value={library.filters.purpose} onChange={(value) => library.setFilter("purpose", value)} /><FilterSelect label="来源" options={library.options.sources} value={library.filters.source} onChange={(value) => library.setFilter("source", value)} /><FilterSelect label="状态" options={library.options.statuses} value={library.filters.status} onChange={(value) => library.setFilter("status", value)} /></div> : null}{activeFilters.length ? <div className="active-filter-chips">{activeFilters.map((key) => <button key={key} onClick={() => library.clearFilter(key)} type="button">{filterLabels[key]}：{statusLabels[library.filters[key]] || library.filters[key]}<IconX size={12} /></button>)}</div> : null}</div>;
}

function FilterSelect({ label, onChange, options, value }) {
  return <label><span>{label}</span><select onChange={(event) => onChange(event.target.value)} value={value}><option value="">全部</option>{options.map((option) => <option key={option} value={option}>{statusLabels[option] || option}</option>)}</select></label>;
}

const filterLabels = { purpose: "用途", source: "来源", status: "状态" };
const statusLabels = { failed: "处理失败", missing: "文件缺失", ready: "可用", running: "生成中" };
