from __future__ import annotations

from app.config import RuntimeConfig
from schemas.settings import (
    AISettingsSection,
    AppSettingsDto,
    BrowserSettingsSection,
    LoggingSettingsSection,
    MediaSettingsSection,
    PathSettingsSection,
    RuntimeSettingsSection,
)
from services.config import ConfigBusSnapshot


def map_legacy_settings(
    snapshot: ConfigBusSnapshot,
    *,
    runtime_config: RuntimeConfig,
    ai_settings: AISettingsSection,
) -> AppSettingsDto:
    values = snapshot.values
    data_root = runtime_config.data_dir
    return AppSettingsDto(
        runtime=RuntimeSettingsSection(
            mode=_string_value(
                values,
                "runtime.mode",
                runtime_config.mode,
            ),
            workspaceRoot=_string_value(
                values,
                "runtime.workspaceRoot",
                str(runtime_config.repo_root),
            ),
        ),
        paths=PathSettingsSection(
            cacheDir=_string_value(
                values,
                "paths.cacheDir",
                str(data_root / "cache"),
            ),
            exportDir=_string_value(
                values,
                "paths.exportDir",
                str(data_root / "exports"),
            ),
            logDir=_string_value(
                values,
                "paths.logDir",
                str(data_root / "logs"),
            ),
        ),
        logging=LoggingSettingsSection(
            level=_string_value(values, "logging.level", "INFO"),
        ),
        ai=ai_settings.model_copy(deep=True),
        media=MediaSettingsSection(
            ffprobePath=_string_value(
                values,
                "media.ffprobePath",
                "",
            ),
            ffmpegPath=_string_value(
                values,
                "media.ffmpegPath",
                "",
            ),
        ),
        browser=BrowserSettingsSection(
            executablePath=_string_value(
                values,
                "browser.executablePath",
                "",
            ),
        ),
        revision=snapshot.revision,
    )


def _string_value(
    values: dict[str, object],
    key: str,
    fallback: str,
) -> str:
    value = values.get(key)
    return value if isinstance(value, str) else fallback
