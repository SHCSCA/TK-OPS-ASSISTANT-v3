export function ResultDataTable({ ariaLabel, children, columns, className = "" }) {
  return <div className={`result-data-table-shell ${className}`.trim()}><table aria-label={ariaLabel} className="result-data-table"><thead><tr>{columns.map((column) => <th className={column.className || ""} key={column.id} scope="col">{column.label}</th>)}</tr></thead><tbody>{children}</tbody></table></div>;
}

export function ResultCheckbox({ checked, label, onChange }) {
  return <label className="result-checkbox"><input aria-label={label} checked={checked} onChange={onChange} type="checkbox" /><span aria-hidden="true" /></label>;
}
