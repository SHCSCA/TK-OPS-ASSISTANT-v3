import { IconFolderOpen } from "@tabler/icons-react";
import { AssetCard } from "./AssetCard.jsx";

export function AssetWall({ assets, onClear, onOpen }) {
  if (!assets.length) return <div className="asset-empty"><IconFolderOpen size={25} /><strong>当前筛选下没有资产</strong><span>清除筛选后恢复当前账号已有内容。</span><button className="secondary-button" onClick={onClear} type="button">清除筛选</button></div>;
  return <div className="asset-wall">{assets.map((asset) => <AssetCard asset={asset} key={asset.id} onOpen={onOpen} />)}</div>;
}
