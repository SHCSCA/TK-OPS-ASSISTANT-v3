from __future__ import annotations

import logging
from pathlib import Path
from typing import Awaitable, Callable

from repositories.imported_video_repository import ImportedVideoRepository
from repositories.video_deconstruction_repository import VideoDeconstructionRepository
from services.ffprobe import probe_video
from services.ws_manager import ws_manager

log = logging.getLogger(__name__)
ProgressCallback = Callable[[int, str], Awaitable[None]]


async def process_video_import_task(
    video_id: str,
    file_path: str,
    repository: ImportedVideoRepository,
    *,
    stage_repository: VideoDeconstructionRepository | None = None,
    progress_callback: ProgressCallback | None = None,
) -> None:
    log.info("开始后台解析视频 %s (%s)", video_id, file_path)
    await _emit_stage_event("video.import.stage.started", video_id, "import", startedAt=_utc_now())

    try:
        path = Path(file_path)
        await _report_progress(progress_callback, 10, "正在读取视频文件")
        if not path.is_file():
            raise FileNotFoundError(f"文件不存在：{file_path}")

        await _report_progress(progress_callback, 40, "正在解析视频元信息")
        probe_result = probe_video(path)

        video = repository.get(video_id)
        if not video:
            log.warning("解析任务找不到对应的视频记录: %s", video_id)
            return

        await _report_progress(progress_callback, 80, "正在保存解析结果")
        if probe_result:
            video.file_size_bytes = probe_result.file_size_bytes
            video.duration_seconds = probe_result.duration_seconds
            video.width = probe_result.width
            video.height = probe_result.height
            video.frame_rate = probe_result.frame_rate
            video.codec = probe_result.codec
            video.status = "ready"
            video.error_message = None
        else:
            video.status = "imported"
            video.error_message = "FFprobe 不可用，已仅记录文件路径和大小。"

        repository.update(video)
        if stage_repository is not None:
            stage_repository.upsert_stage_run(
                video_id,
                "import",
                status="succeeded",
                progress_pct=100,
                result_summary=f"已完成 {video.file_name} 的导入解析",
                error_message=None,
            )

        await _emit_stage_event(
            "video.import.stage.completed",
            video_id,
            "import",
            resultSummary=f"已完成 {video.file_name} 的导入解析",
        )
        await ws_manager.broadcast(
            {
                "event": "video_status_changed",
                "video_id": video_id,
                "status": video.status,
                "file_name": video.file_name,
            }
        )
        log.info("后台解析视频成功: %s", video_id)
    except Exception as exc:
        log.exception("后台解析视频失败: %s", video_id)
        video = repository.get(video_id)
        if video:
            video.status = "error"
            video.error_message = f"解析失败: {str(exc)}"
            repository.update(video)
            if stage_repository is not None:
                stage_repository.upsert_stage_run(
                    video_id,
                    "import",
                    status="failed",
                    progress_pct=0,
                    result_summary=None,
                    error_message=video.error_message,
                )
            await _emit_stage_event(
                "video.import.stage.failed",
                video_id,
                "import",
                errorCode="import.failed",
                errorMessage=video.error_message,
            )
            await ws_manager.broadcast(
                {
                    "event": "video_status_changed",
                    "video_id": video_id,
                    "status": "error",
                    "error_message": video.error_message,
                }
            )
        raise


async def _report_progress(
    progress_callback: ProgressCallback | None,
    progress: int,
    message: str,
) -> None:
    if progress_callback is not None:
        await progress_callback(progress, message)


async def _emit_stage_event(event_type: str, video_id: str, stage: str, **payload: object) -> None:
    await ws_manager.broadcast(
        {
            "type": event_type,
            "videoId": video_id,
            "stage": stage,
            **payload,
        }
    )


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
