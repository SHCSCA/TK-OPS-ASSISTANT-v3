import { IconFileText, IconHeadphones, IconMovie, IconPhoto, IconPhotoOff } from "@tabler/icons-react";

const icons = { audio: IconHeadphones, document: IconFileText, image: IconPhoto, video: IconMovie };
const typeLabels = { audio: "音频", document: "文档", image: "图片", video: "视频" };
const statusLabels = { failed: "处理失败", missing: "文件缺失", ready: "可用", running: "生成中" };

export function AssetCard({ asset, onOpen }) {
  const Icon = icons[asset.type] || IconFileText;
  return <button className={`asset-card asset-card--${asset.status}`} onClick={() => onOpen(asset)} type="button"><span className="asset-preview">{asset.previewUrl ? <img alt={asset.title} src={asset.previewUrl} /> : <><Icon size={26} stroke={1.5} />{asset.type === "image" && asset.metadata?.previewState === "not-generated" ? <small><IconPhotoOff size={12} />无真实预览</small> : null}</>}</span><span className="asset-card__body"><strong>{asset.title}</strong><small>{typeLabels[asset.type]} · {asset.purpose}</small><span><em>{asset.source}</em><b>{asset.version}</b></span></span><span className={`asset-status asset-status--${asset.status}`}>{statusLabels[asset.status] || asset.status}</span></button>;
}
