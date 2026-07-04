from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import quote

from domain.models.asset import Asset
from repositories.asset_repository import AssetRepository
from schemas.workspace import TimelinePreviewErrorDto, TimelinePreviewMediaDto
from services.asset_media_access import create_asset_media_token

log = logging.getLogger(__name__)

PREVIEW_TRACK_KINDS = {"audio", "video"}
PLAYABLE_ASSET_TYPES = {"audio", "video"}
ASSET_MIME_TYPES = {
    ".m4a": "audio/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/mp4",
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
    ".webm": "video/webm",
}


class TimelinePreviewMediaResolver:
    def __init__(self, asset_repository: AssetRepository | None) -> None:
        self._asset_repository = asset_repository

    def resolve(
        self,
        tracks: list[dict[str, object]],
    ) -> tuple[TimelinePreviewMediaDto | None, TimelinePreviewErrorDto | None]:
        asset_ids = self._iter_asset_ids(tracks)
        if not asset_ids:
            return None, None

        if self._asset_repository is None:
            return None, TimelinePreviewErrorDto(
                code="preview.asset_repository_unavailable",
                message="资产服务未就绪，无法生成真实媒体预览。",
            )

        missing_asset_file = False
        playable_media: TimelinePreviewMediaDto | None = None
        for asset_id in asset_ids:
            asset = self._asset_repository.get_asset(asset_id)
            if asset is None:
                log.warning("时间线预览读取资产失败 asset_id=%s detail=资产不存在", asset_id)
                missing_asset_file = True
                continue

            asset_type = str(asset.type or "").strip().lower()
            if asset_type not in PLAYABLE_ASSET_TYPES:
                continue

            asset_path = self._resolve_asset_path(asset)
            if asset_path is None:
                missing_asset_file = True
                continue

            token = create_asset_media_token(asset.id, project_id=asset.project_id)
            if playable_media is None:
                playable_media = TimelinePreviewMediaDto(
                    kind=asset_type,
                    url=f"/api/assets/{quote(asset.id, safe='')}/media?token={quote(token, safe='')}",
                    source=f"asset:{asset.id}",
                    mimeType=self._asset_mime_type(asset_path),
                    durationMs=self._asset_duration_ms(asset),
                    expiresAt=None,
                )

        if missing_asset_file:
            return None, TimelinePreviewErrorDto(
                code="preview.asset_file_missing",
                message="时间线包含资产片段，但源文件不可用，已保留结构预览。",
            )

        if playable_media is not None:
            return playable_media, None

        return None, None

    def _iter_asset_ids(self, tracks: list[dict[str, object]]) -> list[str]:
        asset_ids: list[str] = []
        for track in tracks:
            track_kind = str(track.get("kind") or "")
            if track_kind not in PREVIEW_TRACK_KINDS:
                continue
            clips = track.get("clips")
            if not isinstance(clips, list):
                continue
            for clip in clips:
                if not isinstance(clip, dict):
                    continue
                if str(clip.get("sourceType") or "") != "asset":
                    continue
                asset_id = str(clip.get("sourceId") or "").strip()
                if asset_id:
                    asset_ids.append(asset_id)
        return asset_ids

    def _resolve_asset_path(self, asset: Asset) -> Path | None:
        file_path = str(asset.file_path or "").strip()
        if not file_path:
            log.warning("时间线预览资产缺少文件路径 asset_id=%s", asset.id)
            return None

        try:
            asset_path = Path(file_path)
            if asset_path.exists() and asset_path.is_file():
                return asset_path
            log.warning("时间线预览资产源文件不可用 asset_id=%s path=%s", asset.id, file_path)
            return None
        except OSError:
            log.exception("时间线预览检查资产文件失败 asset_id=%s", asset.id)
            return None

    def _asset_mime_type(self, asset_path: Path) -> str:
        return ASSET_MIME_TYPES.get(asset_path.suffix.lower(), "application/octet-stream")

    def _asset_duration_ms(self, asset: Asset) -> int | None:
        try:
            duration_ms = int(asset.duration_ms) if asset.duration_ms is not None else None
        except (TypeError, ValueError):
            log.warning("时间线预览资产时长无效 asset_id=%s duration_ms=%s", asset.id, asset.duration_ms)
            return None
        if duration_ms is None or duration_ms < 0:
            return None
        return duration_ms
