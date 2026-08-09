import { IconUpload } from "@tabler/icons-react";
import { useMemo } from "react";
import { AssetToolbar } from "../components/content-library/AssetToolbar.jsx";
import { AssetWall } from "../components/content-library/AssetWall.jsx";
import { PageSection } from "../components/PageSection.jsx";
import { filterAssets, normalizeMediaOutput } from "../data/assets.js";
import { PageEmptyState } from "../components/empty-states/PageEmptyState.jsx";
import { resolvePageEmptyState } from "../utils/resolvePageEmptyState.js";

export function ContentLibrary({ state }) {
  const library = state.creative.library;
  const allAssets = useMemo(() => [...library.allAssets, ...state.media.outputs.map((item) => normalizeMediaOutput(item, state.activeAccountId))], [library.allAssets, state.activeAccountId, state.media.outputs]);
  const visibleAssets = useMemo(() => {
    const filtered = filterAssets(allAssets, library.filters);
    if (library.sort === "name") return [...filtered].sort((a, b) => a.title.localeCompare(b.title));
    if (library.sort === "type") return [...filtered].sort((a, b) => a.type.localeCompare(b.type));
    return filtered;
  }, [allAssets, library.filters, library.sort]);
  const emptyState = resolvePageEmptyState("library", state.dataScenario, allAssets.length > 0);
  if (emptyState) return <div className="page-enter"><PageEmptyState definition={emptyState} onAction={() => state.notify("本地文件选择器已打开", "info")} /></div>;
  return <div className="page-stack page-enter"><PageSection title="内容库" meta="视频、图片、音频和文档按当前账号隔离" action={<button className="secondary-button" onClick={() => state.notify("本地文件选择器已打开", "info")} type="button"><IconUpload size={15} />导入</button>}><AssetToolbar library={library} /><AssetWall assets={visibleAssets} onClear={library.clearAllFilters} onOpen={(asset) => state.setDetail({ type: "asset", data: asset })} /></PageSection></div>;
}
