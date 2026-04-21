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

FFPROBE_UNAVAILABLE_MESSAGE = "FFprobe 不可用，视频元数据解析已降级失败，请先修复媒体诊断后重试。"
FFPROBE_UNAVAILABLE_CODE = "media.ffprobe_unavailable"
IMPORT_FAILED_CODE = "video.import.failed"
IMPORT_FILE_MISSING_CODE = "video.import.file_missing"


async def process_video_import_task(
    video_id: str,
    task_id: str,
    file_path: str,
    repository: ImportedVideoRepository,
    *,
    stage_repository: VideoDeconstructionRepository | None = None,
    progress_callback: ProgressCallback | None = None,
) -> None:
    log.info("开始后台解析视频 %s (%s)", video_id, file_path)
    await _emit_stage_event(
        "video.import.stage.started",
        video_id,
        "import",
        taskId=task_id,
        ownerRef=_import_owner_ref(video_id),
        startedAt=_utc_now(),
    )

    try:
        path = Path(file_path)
        await _report_progress(progress_callback, 10, "正在读取视频文件")
        if not path.is_file():
            raise FileNotFoundError(f"文件不存在：{file_path}")

        await _report_progress(progress_callback, 40, "正在解析视频元信息")
        probe_result = probe_video(path)

        video = repository.get(video_id)
        if video is None:
            log.warning("解析任务找不到对应的视频记录: %s", video_id)
            return

        await _report_progress(progress_callback, 80, "正在保存解析结果")
        if probe_result is not None:
            video.file_size_bytes = probe_result.file_size_bytes
            video.duration_seconds = probe_result.duration_seconds
            video.width = probe_result.width
            video.height = probe_result.height
            video.frame_rate = probe_result.frame_rate
            video.codec = probe_result.codec
            video.status = "ready"
            video.error_message = None
        else:
            video.status = "failed_degraded"
            video.error_message = FFPROBE_UNAVAILABLE_MESSAGE

        repository.update(video)
        if stage_repository is not None:
            stage_repository.upsert_stage_run(
                video_id,
                "import",
                status="succeeded" if probe_result is not None else "failed",
                progress_pct=100 if probe_result is not None else 80,
                result_summary=(
                    f"已完成 {video.file_name} 的导入解析"
                    if probe_result is not None
                    else "FFprobe 不可用，导入解析失败，暂缺时长与分辨率等元数据。"
                ),
                error_message=None if probe_result is not None else video.error_message,
            )

        if probe_result is not None:
            await _emit_stage_event(
                "video.import.stage.completed",
                video_id,
                "import",
                taskId=task_id,
                ownerRef=_import_owner_ref(video_id),
                resultSummary=f"已完成 {video.file_name} 的导入解析",
            )
        else:
            await _emit_stage_event(
                "video.import.stage.failed",
                video_id,
                "import",
                taskId=task_id,
                ownerRef=_import_owner_ref(video_id),
                errorCode=FFPROBE_UNAVAILABLE_CODE,
                errorMessage=video.error_message,
                nextAction="请先修复 FFprobe 或媒体诊断配置后，再重新导入视频。",
            )

        await ws_manager.broadcast(
            {
                "event": "video_status_changed",
                "video_id": video_id,
                "status": video.status,
                "file_name": video.file_name,
                "error_message": video.error_message,
            }
        )
        log.info("后台解析视频完成: %s", video_id)
    except Exception as exc:
        log.exception("后台解析视频失败: %s", video_id)
        video = repository.get(video_id)
        if video is not None:
            error_code = _derive_import_error_code(exc)
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
                taskId=task_id,
                ownerRef=_import_owner_ref(video_id),
                errorCode=error_code,
                errorMessage=video.error_message,
                nextAction=_derive_import_next_action(error_code),
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


def _import_owner_ref(video_id: str) -> dict[str, str]:
    return {
        "kind": "video-stage",
        "id": f"{video_id}:import",
        "videoId": video_id,
        "stageId": "import",
    }


def _derive_import_error_code(exc: Exception) -> str:
    if isinstance(exc, FileNotFoundError):
        return IMPORT_FILE_MISSING_CODE
    return IMPORT_FAILED_CODE


def _derive_import_next_action(error_code: str) -> str:
    if error_code == IMPORT_FILE_MISSING_CODE:
        return "请确认原始视频文件仍存在于本地路径后，再重新导入视频。"
    if error_code == FFPROBE_UNAVAILABLE_CODE:
        return "请先修复 FFprobe 或媒体诊断配置后，再重新导入视频。"
    return "请检查视频文件可读性与 Runtime 日志后，再重新导入视频。"
