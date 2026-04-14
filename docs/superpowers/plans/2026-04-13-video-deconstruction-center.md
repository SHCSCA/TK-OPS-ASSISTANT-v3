# 视频拆解中心实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将"视频拆解中心"页面从空壳占位推进到可用状态：用户可以导入本地视频文件，Runtime 自动提取视频元信息（时长、分辨率、帧率、文件大小），并为后续的转写、切段、结构拆解建立数据基线和 UI 骨架。

**Architecture:** 前端通过 Tauri 文件对话框选择本地视频，将路径发送给 Runtime。Runtime 使用 FFprobe（FFmpeg 工具链的一部分）提取元信息并持久化为 `ImportedVideo` 记录，关联到当前 Project。前端展示已导入视频列表和元信息卡片。本轮不实现转写、切段等 AI 能力，只打通"导入 → 元信息提取 → 列表展示"的最小闭环。

**Tech Stack:** Vue 3、TypeScript、Pinia、Tauri 2 File Dialog API、Python FastAPI、FFprobe、SQLAlchemy

**前置依赖:** `2026-04-13-domain-model-foundation` plan 必须先完成。

---

## 边界

- 只实现视频导入和元信息提取，不实现转写、切段、结构拆解
- 不引入新的 AI Provider 调用
- 不改变其他页面的已有功能
- FFprobe 不可用时，降级为只记录文件路径和大小，不阻断导入流程
- 本轮不处理视频文件拷贝到项目工作区（只记录原始路径）

## 前端开发流程

按 CLAUDE.md 约定，前端页面开发遵循固定流程：
1. **Stitch 设计先行** — 使用 Stitch CLI 生成视频拆解中心的设计稿
2. **Gemini 编码实现** — 基于设计稿实现页面组件和交互
3. **Claude 样式校准** — 对照设计稿进行最终视觉还原

## 文件结构

### 新建文件

| 文件 | 职责 |
|------|------|
| `apps/py-runtime/src/domain/models/imported_video.py` | `ImportedVideo` SQLAlchemy 模型 |
| `apps/py-runtime/src/repositories/imported_video_repository.py` | 导入视频数据访问层 |
| `apps/py-runtime/src/services/video_import_service.py` | 视频导入业务逻辑（FFprobe 调用、元信息提取） |
| `apps/py-runtime/src/services/ffprobe.py` | FFprobe 封装（子进程调用、JSON 解析） |
| `apps/py-runtime/src/api/routes/video_deconstruction.py` | `/api/video-deconstruction` 路由 |
| `apps/py-runtime/src/schemas/video_deconstruction.py` | 请求/响应 DTO |
| `apps/desktop/src/stores/video-import.ts` | 视频导入 Pinia store |
| `apps/desktop/src/types/video.ts` | 视频相关前端类型 |
| `tests/runtime/test_video_import_service.py` | 服务层测试 |
| `tests/runtime/test_ffprobe.py` | FFprobe 封装测试 |
| `tests/contracts/test_video_deconstruction_api.py` | API 契约测试 |
| `apps/desktop/tests/video-deconstruction.spec.ts` | 前端测试 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `apps/py-runtime/src/domain/models/__init__.py` | 导出 `ImportedVideo` |
| `apps/py-runtime/src/api/routes/__init__.py` | 注册 `video_deconstruction_router` |
| `apps/py-runtime/src/app/factory.py` | 注入 `VideoImportService`、注册路由 |
| `apps/desktop/src/app/runtime-client.ts` | 新增视频导入相关 API 调用函数 |
| `apps/desktop/src/types/runtime.ts` | 新增视频相关类型 |
| `apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue` | 从占位替换为真实页面 |
| `apps/py-runtime/src/persistence/migrations.py` 或 Alembic | 新增 `imported_videos` 表 migration |

---

## 任务

### Task 1: ImportedVideo 模型与 Migration

**Files:**
- Create: `apps/py-runtime/src/domain/models/imported_video.py`
- Modify: `apps/py-runtime/src/domain/models/__init__.py`
- Test: `tests/runtime/test_domain_models.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/runtime/test_domain_models.py （追加）
from domain.models.imported_video import ImportedVideo


def test_imported_video_table():
    assert ImportedVideo.__tablename__ == "imported_videos"


def test_imported_video_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("imported_videos")}
    expected = {
        "id", "project_id", "file_path", "file_name", "file_size_bytes",
        "duration_seconds", "width", "height", "frame_rate", "codec",
        "status", "error_message", "created_at",
    }
    assert expected == columns


def test_imported_video_belongs_to_project():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        project = Project(
            id="p1", name="项目", description="", status="active",
            current_script_version=0, current_storyboard_version=0,
            created_at="2026-04-13T00:00:00Z",
            updated_at="2026-04-13T00:00:00Z",
            last_accessed_at="2026-04-13T00:00:00Z",
        )
        video = ImportedVideo(
            id="v1", project_id="p1", file_path="/tmp/test.mp4",
            file_name="test.mp4", file_size_bytes=1024000,
            status="ready", created_at="2026-04-13T00:00:00Z",
        )
        session.add_all([project, video])
        session.commit()

        loaded = session.get(ImportedVideo, "v1")
        assert loaded is not None
        assert loaded.project_id == "p1"
        assert loaded.file_name == "test.mp4"
```

- [ ] **Step 2: 运行测试确认失败**
- [ ] **Step 3: 实现 ImportedVideo 模型**

```python
# apps/py-runtime/src/domain/models/imported_video.py
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class ImportedVideo(Base):
    """导入的视频文件及其元信息。"""

    __tablename__ = "imported_videos"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False,
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    codec: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
```

- [ ] **Step 4: 运行测试确认通过**
- [ ] **Step 5: 生成 Alembic migration**

运行: `cd apps/py-runtime && venv\\Scripts\\python.exe -m alembic revision --autogenerate -m "add imported_videos table"`

- [ ] **Step 6: 提交**

```bash
git add apps/py-runtime/src/domain/models/imported_video.py apps/py-runtime/src/domain/models/__init__.py apps/py-runtime/alembic/ tests/runtime/test_domain_models.py
git commit -m "feat: 添加 ImportedVideo 模型和 migration"
```

---

### Task 2: FFprobe 封装

**Files:**
- Create: `apps/py-runtime/src/services/ffprobe.py`
- Test: `tests/runtime/test_ffprobe.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/runtime/test_ffprobe.py
from __future__ import annotations

from services.ffprobe import parse_ffprobe_output, FfprobeResult


def test_parse_valid_ffprobe_json():
    raw = {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30/1",
                "duration": "120.5",
            }
        ],
        "format": {
            "duration": "120.5",
            "size": "5000000",
        },
    }
    result = parse_ffprobe_output(raw)
    assert isinstance(result, FfprobeResult)
    assert result.duration_seconds == 120.5
    assert result.width == 1920
    assert result.height == 1080
    assert result.frame_rate == 30.0
    assert result.codec == "h264"
    assert result.file_size_bytes == 5000000


def test_parse_audio_only_stream():
    raw = {
        "streams": [{"codec_type": "audio", "codec_name": "aac"}],
        "format": {"duration": "60.0", "size": "1000000"},
    }
    result = parse_ffprobe_output(raw)
    assert result.width is None
    assert result.height is None
    assert result.frame_rate is None
    assert result.duration_seconds == 60.0


def test_parse_missing_format_duration():
    raw = {"streams": [], "format": {}}
    result = parse_ffprobe_output(raw)
    assert result.duration_seconds is None
    assert result.file_size_bytes is None
```

- [ ] **Step 2: 运行测试确认失败**
- [ ] **Step 3: 实现 FFprobe 封装**

```python
# apps/py-runtime/src/services/ffprobe.py
from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FfprobeResult:
    """FFprobe 提取的视频元信息。"""
    duration_seconds: float | None
    width: int | None
    height: int | None
    frame_rate: float | None
    codec: str | None
    file_size_bytes: int | None


def probe_video(file_path: Path) -> FfprobeResult | None:
    """调用 FFprobe 提取视频元信息。FFprobe 不可用时返回 None。"""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_streams", "-show_format",
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            log.warning("FFprobe 返回非零退出码: %d", result.returncode)
            return None
        raw = json.loads(result.stdout)
        return parse_ffprobe_output(raw)
    except FileNotFoundError:
        log.warning("FFprobe 未安装或不在 PATH 中")
        return None
    except Exception:
        log.exception("FFprobe 调用失败")
        return None


def parse_ffprobe_output(raw: dict) -> FfprobeResult:
    """解析 FFprobe JSON 输出为结构化结果。"""
    video_stream = None
    for stream in raw.get("streams", []):
        if stream.get("codec_type") == "video":
            video_stream = stream
            break

    fmt = raw.get("format", {})

    duration_raw = (
        (video_stream or {}).get("duration")
        or fmt.get("duration")
    )
    duration = float(duration_raw) if duration_raw else None

    size_raw = fmt.get("size")
    file_size = int(size_raw) if size_raw else None

    width = video_stream.get("width") if video_stream else None
    height = video_stream.get("height") if video_stream else None
    codec = video_stream.get("codec_name") if video_stream else None

    frame_rate = None
    if video_stream and video_stream.get("r_frame_rate"):
        frame_rate = _parse_frame_rate(video_stream["r_frame_rate"])

    return FfprobeResult(
        duration_seconds=duration,
        width=width,
        height=height,
        frame_rate=frame_rate,
        codec=codec,
        file_size_bytes=file_size,
    )


def _parse_frame_rate(value: str) -> float | None:
    """解析 '30/1' 或 '29.97' 格式的帧率。"""
    try:
        if "/" in value:
            num, den = value.split("/", 1)
            denominator = float(den)
            if denominator == 0:
                return None
            return round(float(num) / denominator, 2)
        return round(float(value), 2)
    except (ValueError, ZeroDivisionError):
        return None
```

- [ ] **Step 4: 运行测试确认通过**
- [ ] **Step 5: 提交**

```bash
git add apps/py-runtime/src/services/ffprobe.py tests/runtime/test_ffprobe.py
git commit -m "feat: 添加 FFprobe 封装和元信息解析"
```

---

### Task 3: VideoImportService 与 Repository

**Files:**
- Create: `apps/py-runtime/src/repositories/imported_video_repository.py`
- Create: `apps/py-runtime/src/services/video_import_service.py`
- Test: `tests/runtime/test_video_import_service.py`

- [ ] **Step 1: 编写 Repository 和 Service 的失败测试**

```python
# tests/runtime/test_video_import_service.py
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from domain.models import Base
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.imported_video_repository import ImportedVideoRepository
from services.video_import_service import VideoImportService
from services.ffprobe import FfprobeResult


def _setup():
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test.db"
    engine = create_runtime_engine(db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    # 插入一个测试项目
    from domain.models.project import Project
    with session_factory() as session:
        session.add(Project(
            id="p1", name="测试", description="", status="active",
            current_script_version=0, current_storyboard_version=0,
            created_at="2026-04-13T00:00:00Z",
            updated_at="2026-04-13T00:00:00Z",
            last_accessed_at="2026-04-13T00:00:00Z",
        ))
        session.commit()
    repo = ImportedVideoRepository(session_factory=session_factory)
    service = VideoImportService(repository=repo)
    return service, tmpdir


def test_import_video_with_ffprobe_available():
    service, tmpdir = _setup()
    fake_video = Path(tmpdir) / "test.mp4"
    fake_video.write_bytes(b"\x00" * 1024)

    mock_result = FfprobeResult(
        duration_seconds=60.0, width=1920, height=1080,
        frame_rate=30.0, codec="h264", file_size_bytes=1024,
    )
    with patch("services.video_import_service.probe_video", return_value=mock_result):
        video = service.import_video(project_id="p1", file_path=str(fake_video))

    assert video["status"] == "ready"
    assert video["width"] == 1920
    assert video["duration_seconds"] == 60.0


def test_import_video_without_ffprobe():
    service, tmpdir = _setup()
    fake_video = Path(tmpdir) / "test.mp4"
    fake_video.write_bytes(b"\x00" * 2048)

    with patch("services.video_import_service.probe_video", return_value=None):
        video = service.import_video(project_id="p1", file_path=str(fake_video))

    assert video["status"] == "imported"
    assert video["file_size_bytes"] == 2048
    assert video["width"] is None


def test_import_nonexistent_file_raises():
    service, tmpdir = _setup()
    import pytest
    with pytest.raises(Exception):
        service.import_video(project_id="p1", file_path="/nonexistent/video.mp4")


def test_list_videos_for_project():
    service, tmpdir = _setup()
    fake_video = Path(tmpdir) / "a.mp4"
    fake_video.write_bytes(b"\x00" * 512)

    with patch("services.video_import_service.probe_video", return_value=None):
        service.import_video(project_id="p1", file_path=str(fake_video))

    videos = service.list_videos(project_id="p1")
    assert len(videos) == 1
    assert videos[0]["file_name"] == "a.mp4"
```

- [ ] **Step 2: 运行测试确认失败**
- [ ] **Step 3: 实现 ImportedVideoRepository**

```python
# apps/py-runtime/src/repositories/imported_video_repository.py
from __future__ import annotations

import logging

from sqlalchemy.orm import Session, sessionmaker

from domain.models.imported_video import ImportedVideo

log = logging.getLogger(__name__)


class ImportedVideoRepository:
    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create(self, video: ImportedVideo) -> ImportedVideo:
        with self._session_factory() as session:
            session.add(video)
            session.commit()
            session.refresh(video)
            return video

    def list_by_project(self, project_id: str) -> list[ImportedVideo]:
        with self._session_factory() as session:
            return list(
                session.query(ImportedVideo)
                .filter_by(project_id=project_id)
                .order_by(ImportedVideo.created_at.desc())
                .all()
            )

    def get_by_id(self, video_id: str) -> ImportedVideo | None:
        with self._session_factory() as session:
            return session.get(ImportedVideo, video_id)

    def delete(self, video_id: str) -> bool:
        with self._session_factory() as session:
            video = session.get(ImportedVideo, video_id)
            if video is None:
                return False
            session.delete(video)
            session.commit()
            return True
```

- [ ] **Step 4: 实现 VideoImportService**

```python
# apps/py-runtime/src/services/video_import_service.py
from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException

from domain.models.base import generate_uuid
from domain.models.imported_video import ImportedVideo
from repositories.imported_video_repository import ImportedVideoRepository
from services.ffprobe import FfprobeResult, probe_video

log = logging.getLogger(__name__)


class VideoImportService:
    def __init__(self, *, repository: ImportedVideoRepository) -> None:
        self._repository = repository

    def import_video(self, *, project_id: str, file_path: str) -> dict:
        """导入视频文件，提取元信息并持久化。"""
        path = Path(file_path)
        if not path.is_file():
            raise HTTPException(status_code=400, detail="视频文件不存在。")

        file_size = path.stat().st_size
        probe_result = probe_video(path)

        if probe_result is not None:
            video = ImportedVideo(
                id=generate_uuid(),
                project_id=project_id,
                file_path=str(path),
                file_name=path.name,
                file_size_bytes=probe_result.file_size_bytes or file_size,
                duration_seconds=probe_result.duration_seconds,
                width=probe_result.width,
                height=probe_result.height,
                frame_rate=probe_result.frame_rate,
                codec=probe_result.codec,
                status="ready",
                created_at=_utc_now(),
            )
        else:
            video = ImportedVideo(
                id=generate_uuid(),
                project_id=project_id,
                file_path=str(path),
                file_name=path.name,
                file_size_bytes=file_size,
                status="imported",
                error_message="FFprobe 不可用，元信息未提取。",
                created_at=_utc_now(),
            )

        saved = self._repository.create(video)
        log.info("视频导入成功: %s (project=%s)", saved.file_name, project_id)
        return _to_dict(saved)

    def list_videos(self, *, project_id: str) -> list[dict]:
        videos = self._repository.list_by_project(project_id)
        return [_to_dict(v) for v in videos]

    def delete_video(self, *, video_id: str) -> None:
        if not self._repository.delete(video_id):
            raise HTTPException(status_code=404, detail="视频记录不存在。")


def _to_dict(video: ImportedVideo) -> dict:
    return {
        "id": video.id,
        "projectId": video.project_id,
        "filePath": video.file_path,
        "fileName": video.file_name,
        "fileSizeBytes": video.file_size_bytes,
        "durationSeconds": video.duration_seconds,
        "width": video.width,
        "height": video.height,
        "frameRate": video.frame_rate,
        "codec": video.codec,
        "status": video.status,
        "errorMessage": video.error_message,
        "createdAt": video.created_at,
    }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
```

- [ ] **Step 5: 运行测试确认通过**
- [ ] **Step 6: 提交**

```bash
git add apps/py-runtime/src/repositories/imported_video_repository.py apps/py-runtime/src/services/video_import_service.py apps/py-runtime/src/services/ffprobe.py tests/runtime/test_video_import_service.py
git commit -m "feat: 添加视频导入服务和 Repository"
```

---

### Task 4: API 路由与 DTO

**Files:**
- Create: `apps/py-runtime/src/schemas/video_deconstruction.py`
- Create: `apps/py-runtime/src/api/routes/video_deconstruction.py`
- Modify: `apps/py-runtime/src/api/routes/__init__.py`
- Modify: `apps/py-runtime/src/app/factory.py`
- Test: `tests/contracts/test_video_deconstruction_api.py`

- [ ] **Step 1: 编写 API 契约测试**

```python
# tests/contracts/test_video_deconstruction_api.py
from __future__ import annotations


def test_import_video_request_shape():
    """验证导入视频请求的 JSON 结构。"""
    request_body = {"filePath": "/path/to/video.mp4"}
    assert "filePath" in request_body
    assert isinstance(request_body["filePath"], str)


def test_imported_video_response_shape():
    """验证导入视频响应的 JSON 信封结构。"""
    response = {
        "ok": True,
        "data": {
            "id": "abc123",
            "projectId": "p1",
            "filePath": "/path/to/video.mp4",
            "fileName": "video.mp4",
            "fileSizeBytes": 1024000,
            "durationSeconds": 60.0,
            "width": 1920,
            "height": 1080,
            "frameRate": 30.0,
            "codec": "h264",
            "status": "ready",
            "errorMessage": None,
            "createdAt": "2026-04-13T00:00:00Z",
        },
    }
    assert response["ok"] is True
    data = response["data"]
    assert all(key in data for key in [
        "id", "projectId", "fileName", "fileSizeBytes", "status", "createdAt",
    ])


def test_video_list_response_shape():
    """验证视频列表响应的 JSON 信封结构。"""
    response = {
        "ok": True,
        "data": [
            {"id": "v1", "fileName": "a.mp4", "status": "ready"},
        ],
    }
    assert response["ok"] is True
    assert isinstance(response["data"], list)
```

- [ ] **Step 2: 实现 DTO**

```python
# apps/py-runtime/src/schemas/video_deconstruction.py
from __future__ import annotations

from pydantic import BaseModel


class ImportVideoInput(BaseModel):
    filePath: str


class ImportedVideoDto(BaseModel):
    id: str
    projectId: str
    filePath: str
    fileName: str
    fileSizeBytes: int
    durationSeconds: float | None = None
    width: int | None = None
    height: int | None = None
    frameRate: float | None = None
    codec: str | None = None
    status: str
    errorMessage: str | None = None
    createdAt: str
```

- [ ] **Step 3: 实现 API 路由**

```python
# apps/py-runtime/src/api/routes/video_deconstruction.py
from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.envelope import success_response
from schemas.video_deconstruction import ImportVideoInput

router = APIRouter(prefix="/api/video-deconstruction", tags=["video-deconstruction"])


@router.post("/projects/{project_id}/import")
async def import_video(project_id: str, body: ImportVideoInput, request: Request):
    service = request.app.state.video_import_service
    result = service.import_video(project_id=project_id, file_path=body.filePath)
    return success_response(result)


@router.get("/projects/{project_id}/videos")
async def list_videos(project_id: str, request: Request):
    service = request.app.state.video_import_service
    result = service.list_videos(project_id=project_id)
    return success_response(result)


@router.delete("/videos/{video_id}")
async def delete_video(video_id: str, request: Request):
    service = request.app.state.video_import_service
    service.delete_video(video_id=video_id)
    return success_response(None)
```

- [ ] **Step 4: 在 `__init__.py` 和 `factory.py` 中注册**
- [ ] **Step 5: 运行全部测试确认通过**
- [ ] **Step 6: 提交**

```bash
git add apps/py-runtime/src/schemas/video_deconstruction.py apps/py-runtime/src/api/routes/video_deconstruction.py apps/py-runtime/src/api/routes/__init__.py apps/py-runtime/src/app/factory.py tests/contracts/test_video_deconstruction_api.py
git commit -m "feat: 添加视频拆解 API 路由和 DTO"
```

---

### Task 5: 前端类型与 Runtime Client

**Files:**
- Create: `apps/desktop/src/types/video.ts`
- Modify: `apps/desktop/src/types/runtime.ts`
- Modify: `apps/desktop/src/app/runtime-client.ts`

- [ ] **Step 1: 定义前端视频类型**

```typescript
// apps/desktop/src/types/video.ts
export interface ImportedVideo {
  id: string;
  projectId: string;
  filePath: string;
  fileName: string;
  fileSizeBytes: number;
  durationSeconds: number | null;
  width: number | null;
  height: number | null;
  frameRate: number | null;
  codec: string | null;
  status: "imported" | "ready";
  errorMessage: string | null;
  createdAt: string;
}
```

- [ ] **Step 2: 在 runtime-client.ts 新增 API 调用函数**

```typescript
// apps/desktop/src/app/runtime-client.ts （追加）
import type { ImportedVideo } from "@/types/video";

export async function importVideo(
  projectId: string,
  filePath: string
): Promise<ImportedVideo> {
  return requestRuntime<ImportedVideo>(
    `/api/video-deconstruction/projects/${projectId}/import`,
    { body: JSON.stringify({ filePath }), method: "POST" }
  );
}

export async function fetchImportedVideos(
  projectId: string
): Promise<ImportedVideo[]> {
  return requestRuntime<ImportedVideo[]>(
    `/api/video-deconstruction/projects/${projectId}/videos`
  );
}

export async function deleteImportedVideo(videoId: string): Promise<void> {
  return requestRuntime<void>(
    `/api/video-deconstruction/videos/${videoId}`,
    { method: "DELETE" }
  );
}
```

- [ ] **Step 3: 提交**

```bash
git add apps/desktop/src/types/video.ts apps/desktop/src/app/runtime-client.ts
git commit -m "feat: 添加视频导入前端类型和 API 调用"
```

---

### Task 6: Pinia Store — video-import

**Files:**
- Create: `apps/desktop/src/stores/video-import.ts`
- Test: `apps/desktop/tests/video-deconstruction.spec.ts`

- [ ] **Step 1: 实现 video-import store**

```typescript
// apps/desktop/src/stores/video-import.ts
import { defineStore } from "pinia";
import { ref } from "vue";
import type { ImportedVideo } from "@/types/video";
import {
  importVideo as apiImportVideo,
  fetchImportedVideos,
  deleteImportedVideo,
} from "@/app/runtime-client";

export const useVideoImportStore = defineStore("video-import", () => {
  const videos = ref<ImportedVideo[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const importing = ref(false);

  async function loadVideos(projectId: string) {
    loading.value = true;
    error.value = null;
    try {
      videos.value = await fetchImportedVideos(projectId);
    } catch (e: any) {
      error.value = e.message ?? "加载视频列表失败。";
    } finally {
      loading.value = false;
    }
  }

  async function importVideoFile(projectId: string, filePath: string) {
    importing.value = true;
    error.value = null;
    try {
      const video = await apiImportVideo(projectId, filePath);
      videos.value.unshift(video);
    } catch (e: any) {
      error.value = e.message ?? "导入视频失败。";
    } finally {
      importing.value = false;
    }
  }

  async function removeVideo(videoId: string) {
    try {
      await deleteImportedVideo(videoId);
      videos.value = videos.value.filter((v) => v.id !== videoId);
    } catch (e: any) {
      error.value = e.message ?? "删除视频失败。";
    }
  }

  return { videos, loading, error, importing, loadVideos, importVideoFile, removeVideo };
});
```

- [ ] **Step 2: 编写前端测试**

```typescript
// apps/desktop/tests/video-deconstruction.spec.ts
import { describe, it, expect } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useVideoImportStore } from "@/stores/video-import";

describe("VideoImportStore", () => {
  it("初始化状态正确", () => {
    setActivePinia(createPinia());
    const store = useVideoImportStore();
    expect(store.videos).toEqual([]);
    expect(store.loading).toBe(false);
    expect(store.importing).toBe(false);
    expect(store.error).toBeNull();
  });
});
```

- [ ] **Step 3: 运行前端测试确认通过**

运行: `npm --prefix apps/desktop run test`

- [ ] **Step 4: 提交**

```bash
git add apps/desktop/src/stores/video-import.ts apps/desktop/tests/video-deconstruction.spec.ts
git commit -m "feat: 添加视频导入 Pinia store"
```

---

### Task 7: 页面设计与实现（Stitch → Gemini → Claude）

**Files:**
- Modify: `apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue`

本任务遵循前端页面开发流程：

- [ ] **Step 1: Stitch 设计**

使用 Stitch CLI 生成视频拆解中心设计稿，输出到 `design-drafts/video-deconstruction/`。

设计要点：
- 页面顶部：标题"视频拆解中心" + 导入按钮
- 主体：已导入视频的卡片列表（文件名、时长、分辨率、文件大小、状态徽标）
- 空态：无视频时的引导提示
- 卡片支持删除操作

- [ ] **Step 2: 指派 Gemini 编码实现**

```bash
/ask gemini "基于 design-drafts/video-deconstruction/ 的设计稿，实现 VideoDeconstructionCenterPage.vue 页面。
要求：
1. 使用 Tauri 文件对话框让用户选择视频文件
2. 调用 useVideoImportStore 管理状态
3. 覆盖加载中、空态、正常列表、导入中、错误五种状态
4. 卡片展示文件名、时长、分辨率、文件大小、编码格式
5. 支持删除操作
6. 使用 CSS Variables 和设计令牌
涉及文件: apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue"
```

- [ ] **Step 3: Claude 样式校准**

对照 Stitch 设计稿检查 Gemini 实现的视觉效果，调整间距、颜色、字号等样式细节使其与设计稿一致。

- [ ] **Step 4: 运行前端测试确认通过**
- [ ] **Step 5: 提交**

```bash
git add apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue design-drafts/
git commit -m "feat: 实现视频拆解中心页面"
```

---

### Task 8: 端到端验证

- [ ] **Step 1: 运行全部测试**

```bash
npm --prefix apps/desktop run test
venv\\Scripts\\python.exe -m pytest tests/ -q
```

- [ ] **Step 2: 一键启动验证**

运行: `npm run app:dev`

验证清单：
1. 首启授权流程正常
2. 创建项目后切换到视频拆解中心
3. 点击导入按钮弹出文件选择对话框
4. 选择视频文件后卡片出现在列表中
5. 元信息（时长、分辨率等）正确展示（FFprobe 可用时）
6. FFprobe 不可用时显示"已导入"状态和提示
7. 删除操作正常
8. 回到创作总览、脚本中心、分镜中心功能无回归

- [ ] **Step 3: 提交最终修正（如有）**

```bash
git add -A
git commit -m "fix: 视频拆解中心端到端验证修正"
```
