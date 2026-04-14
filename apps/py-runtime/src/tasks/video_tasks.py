from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from repositories.imported_video_repository import ImportedVideoRepository
from services.ffprobe import probe_video
from services.ws_manager import ws_manager

log = logging.getLogger(__name__)


async def process_video_import_task(
    video_id: str,
    file_path: str,
    repository: ImportedVideoRepository,
) -> None:
    """
    后台任务：解析视频元信息并通过 WebSocket 通知前端。
    """
    log.info(f"开始后台解析视频: {video_id} ({file_path})")
    
    try:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 模拟长时间解析，方便在 UI 上观察“呼吸”动画
        # await asyncio.sleep(2) 

        probe_result = probe_video(path)
        
        # 刷新数据库记录
        video = repository.get(video_id)
        if not video:
            log.warning(f"解析任务找不到对应的视频记录: {video_id}")
            return

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
        
        # 通过 WebSocket 广播状态变更
        await ws_manager.broadcast({
            "event": "video_status_changed",
            "video_id": video_id,
            "status": video.status,
            "file_name": video.file_name,
        })
        
        log.info(f"后台解析视频成功: {video_id}")

    except Exception as e:
        log.exception(f"后台解析视频失败: {video_id}, 错误: {e}")
        
        # 记录错误到数据库
        video = repository.get(video_id)
        if video:
            video.status = "error"
            video.error_message = f"解析失败: {str(e)}"
            repository.update(video)
            
            await ws_manager.broadcast({
                "event": "video_status_changed",
                "video_id": video_id,
                "status": "error",
                "error_message": video.error_message,
            })
