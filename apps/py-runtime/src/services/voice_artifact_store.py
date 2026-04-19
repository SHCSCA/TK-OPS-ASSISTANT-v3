from __future__ import annotations

import logging
from pathlib import Path

from fastapi import HTTPException

from services.settings_service import SettingsService

log = logging.getLogger(__name__)


class VoiceArtifactStore:
    def __init__(self, *, settings_service: SettingsService) -> None:
        self._settings_service = settings_service

    def write_audio(
        self,
        track_id: str,
        *,
        audio_bytes: bytes,
        output_format: str,
    ) -> str:
        try:
            workspace_root = Path(self._settings_service.get_settings().runtime.workspaceRoot)
            voice_dir = workspace_root / 'voice'
            voice_dir.mkdir(parents=True, exist_ok=True)
            normalized_format = output_format.strip().lower() or 'mp3'
            output_path = voice_dir / f'{track_id}.{normalized_format}'
            output_path.write_bytes(audio_bytes)
            return str(output_path)
        except Exception as exc:
            log.exception('写入配音文件失败: track=%s', track_id)
            raise HTTPException(status_code=500, detail='写入配音文件失败。') from exc
