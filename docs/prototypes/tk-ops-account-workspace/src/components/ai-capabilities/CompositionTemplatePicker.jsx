import { IconMovie, IconPhoto, IconTypography } from "@tabler/icons-react";

const icons = { static: IconTypography, image: IconPhoto, video: IconMovie };

export function CompositionTemplatePicker({ templates }) {
  return <div className="template-picker">{templates.map((template) => {
    const Icon = icons[template.templateType] || IconTypography;
    return <article key={template.id}><span><Icon size={18} /></span><div><strong>{template.name}</strong><small>{template.aspectRatio} · {template.parameterSummary}</small></div><i>v{template.version}</i></article>;
  })}</div>;
}
