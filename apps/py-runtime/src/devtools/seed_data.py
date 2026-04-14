from __future__ import annotations

import argparse
import json
import mimetypes
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable, Sequence

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import load_runtime_config
from domain.models import (
    AIJobRecord,
    Account,
    Asset,
    AutomationTask,
    Base,
    DeviceWorkspace,
    ExecutionBinding,
    ImportedVideo,
    Project,
    PublishPlan,
    RenderTask,
    ScriptVersion,
    SessionContext,
    StoryboardVersion,
    SubtitleTrack,
    Timeline,
    VoiceTrack,
)
from persistence.engine import create_runtime_engine, create_session_factory

DEV_SEED_SOURCE = "dev_seed"
DEV_SEED_ID_PREFIX = "dev-seed-"

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_BYTES_BY_KIND = {
    "video": 512 * 1024 * 1024,
    "image": 40 * 1024 * 1024,
    "document": 80 * 1024 * 1024,
}


@dataclass(frozen=True, slots=True)
class LocalAssetCandidate:
    kind: str
    path: Path
    file_name: str
    file_size_bytes: int
    mime_type: str | None
    modified_at: str


@dataclass(frozen=True, slots=True)
class SeedOptions:
    database_path: Path
    asset_roots: Sequence[Path]
    reset_dev_seed: bool
    video_limit: int = 12
    image_limit: int = 24
    document_limit: int = 12


@dataclass(frozen=True, slots=True)
class SeedResult:
    database_path: Path
    seeded_projects: int
    seeded_assets: int
    scanned_assets: int


def default_asset_roots() -> tuple[Path, Path, Path]:
    user_home = Path(os.environ.get("USERPROFILE", str(Path.home())))
    return (
        user_home / "Videos",
        user_home / "Pictures",
        user_home / "Documents",
    )


def scan_local_assets(
    *,
    roots: Sequence[Path],
    video_limit: int,
    image_limit: int,
    document_limit: int,
) -> list[LocalAssetCandidate]:
    grouped: dict[str, list[LocalAssetCandidate]] = {
        "video": [],
        "image": [],
        "document": [],
    }
    for root in roots:
        if not root.exists():
            continue
        for file_path in _iter_files(root):
            kind = _asset_kind(file_path)
            if kind is None:
                continue
            try:
                stat = file_path.stat()
            except OSError:
                continue
            if stat.st_size > MAX_BYTES_BY_KIND[kind]:
                continue
            grouped[kind].append(
                LocalAssetCandidate(
                    kind=kind,
                    path=file_path,
                    file_name=file_path.name,
                    file_size_bytes=stat.st_size,
                    mime_type=mimetypes.guess_type(file_path.name)[0],
                    modified_at=datetime.fromtimestamp(
                        stat.st_mtime,
                        tz=UTC,
                    )
                    .isoformat()
                    .replace("+00:00", "Z"),
                )
            )

    limits = {
        "video": video_limit,
        "image": image_limit,
        "document": document_limit,
    }
    selected: list[LocalAssetCandidate] = []
    for kind in ("video", "image", "document"):
        selected.extend(
            sorted(
                grouped[kind],
                key=lambda item: (item.modified_at, -item.file_size_bytes, str(item.path)),
                reverse=True,
            )[: limits[kind]]
        )
    return selected


def seed_dev_data(options: SeedOptions) -> SeedResult:
    engine = create_runtime_engine(options.database_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    candidates = scan_local_assets(
        roots=options.asset_roots,
        video_limit=options.video_limit,
        image_limit=options.image_limit,
        document_limit=options.document_limit,
    )

    with session_factory() as session:
        if options.reset_dev_seed:
            _clear_dev_seed(session)
        _insert_seed_graph(session, candidates)
        session.commit()

    return SeedResult(
        database_path=options.database_path,
        seeded_projects=2,
        seeded_assets=len(candidates),
        scanned_assets=len(candidates),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed TK-OPS Runtime dev data.")
    parser.add_argument("--reset-dev-seed", action="store_true")
    parser.add_argument("--video-limit", type=int, default=12)
    parser.add_argument("--image-limit", type=int, default=24)
    parser.add_argument("--document-limit", type=int, default=12)
    parser.add_argument("--database-path", type=Path, default=None)
    args = parser.parse_args(argv)

    runtime_config = load_runtime_config()
    result = seed_dev_data(
        SeedOptions(
            database_path=(args.database_path or runtime_config.database_path).resolve(),
            asset_roots=default_asset_roots(),
            reset_dev_seed=args.reset_dev_seed,
            video_limit=args.video_limit,
            image_limit=args.image_limit,
            document_limit=args.document_limit,
        )
    )
    print(
        json.dumps(
            {
                "ok": True,
                "databasePath": str(result.database_path),
                "seededProjects": result.seeded_projects,
                "seededAssets": result.seeded_assets,
            },
            ensure_ascii=False,
        )
    )
    return 0


def _iter_files(root: Path) -> Iterable[Path]:
    try:
        for item in root.rglob("*"):
            if item.is_file():
                yield item
    except OSError:
        return


def _asset_kind(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in DOCUMENT_EXTENSIONS:
        return "document"
    return None


def _clear_dev_seed(session: Session) -> None:
    for model in (
        PublishPlan,
        AutomationTask,
        RenderTask,
        SubtitleTrack,
        VoiceTrack,
        Timeline,
        ExecutionBinding,
        DeviceWorkspace,
        Account,
        ImportedVideo,
        Asset,
    ):
        session.execute(delete(model).where(model.id.like(f"{DEV_SEED_ID_PREFIX}%")))

    session.execute(
        delete(StoryboardVersion).where(StoryboardVersion.source == DEV_SEED_SOURCE)
    )
    session.execute(delete(ScriptVersion).where(ScriptVersion.source == DEV_SEED_SOURCE))
    session.execute(delete(AIJobRecord).where(AIJobRecord.id.like(f"{DEV_SEED_ID_PREFIX}%")))
    session.execute(delete(Project).where(Project.id.like(f"{DEV_SEED_ID_PREFIX}%")))
    context = session.get(SessionContext, 1)
    if context is not None and (context.current_project_id or "").startswith(
        DEV_SEED_ID_PREFIX
    ):
        session.delete(context)


def _insert_seed_graph(
    session: Session,
    candidates: Sequence[LocalAssetCandidate],
) -> None:
    now = _utc_now()
    later = (datetime.now(UTC) + timedelta(days=1)).isoformat().replace("+00:00", "Z")
    project_main = Project(
        id="dev-seed-project-ai-video-hub",
        name="TikTok AI 爆款短视频样例",
        description="开发种子项目：从选题、脚本、分镜到发布复盘的完整链路。",
        status="active",
        current_script_version=1,
        current_storyboard_version=1,
        created_at=now,
        updated_at=now,
        last_accessed_at=now,
    )
    project_import = Project(
        id="dev-seed-project-import-remix",
        name="本地素材拆解重制样例",
        description="开发种子项目：从本机素材索引进入视频拆解中心。",
        status="active",
        current_script_version=1,
        current_storyboard_version=1,
        created_at=now,
        updated_at=now,
        last_accessed_at=now,
    )
    session.add_all([project_main, project_import])
    context = session.get(SessionContext, 1)
    if context is None:
        session.add(
            SessionContext(
                id=1,
                current_project_id=project_main.id,
                updated_at=now,
            )
        )
    elif (context.current_project_id or "").startswith(DEV_SEED_ID_PREFIX):
        context.current_project_id = project_main.id
        context.updated_at = now
    elif context.current_project_id is None:
        context.current_project_id = project_main.id
        context.updated_at = now
    session.flush()
    session.add_all(
        [
            AIJobRecord(
                id="dev-seed-ai-job-script",
                project_id=project_main.id,
                capability_id="script_generation",
                provider="openai",
                model="gpt-5.4",
                status="succeeded",
                error=None,
                duration_ms=1840,
                provider_request_id="dev-seed-script-request",
                created_at=now,
                completed_at=now,
            ),
            AIJobRecord(
                id="dev-seed-ai-job-storyboard",
                project_id=project_main.id,
                capability_id="storyboard_generation",
                provider="openai",
                model="gpt-5.4",
                status="succeeded",
                error=None,
                duration_ms=2260,
                provider_request_id="dev-seed-storyboard-request",
                created_at=now,
                completed_at=now,
            ),
        ]
    )
    session.flush()
    session.add_all(
        [
            ScriptVersion(
                project_id=project_main.id,
                revision=1,
                source=DEV_SEED_SOURCE,
                content="用 30 秒讲清一个省时省心的 AI 视频创作流程，开头强调痛点，中段展示自动分镜与配音，结尾引导保存模板。",
                provider="openai",
                model="gpt-5.4",
                ai_job_id="dev-seed-ai-job-script",
                created_at=now,
            ),
            ScriptVersion(
                project_id=project_import.id,
                revision=1,
                source=DEV_SEED_SOURCE,
                content="导入本机视频素材，提取节奏和画面信息后重制为 TikTok 竖版短片。",
                provider=None,
                model=None,
                ai_job_id=None,
                created_at=now,
            ),
            StoryboardVersion(
                project_id=project_main.id,
                revision=1,
                based_on_script_revision=1,
                source=DEV_SEED_SOURCE,
                scenes_json=_json(
                    [
                        {"sceneId": "s1", "title": "痛点开场", "summary": "展示素材堆积与剪辑压力。"},
                        {"sceneId": "s2", "title": "AI 编排", "summary": "脚本、分镜、配音、字幕串联。"},
                        {"sceneId": "s3", "title": "发布闭环", "summary": "渲染后进入账号与设备绑定发布。"},
                    ]
                ),
                provider="openai",
                model="gpt-5.4",
                ai_job_id="dev-seed-ai-job-storyboard",
                created_at=now,
            ),
            StoryboardVersion(
                project_id=project_import.id,
                revision=1,
                based_on_script_revision=1,
                source=DEV_SEED_SOURCE,
                scenes_json=_json(
                    [
                        {"sceneId": "s1", "title": "导入素材", "summary": "选择本地视频并读取元信息。"},
                        {"sceneId": "s2", "title": "重制方向", "summary": "保留节奏，替换脚本和字幕。"},
                    ]
                ),
                provider=None,
                model=None,
                ai_job_id=None,
                created_at=now,
            ),
        ]
    )
    session.flush()

    timeline = Timeline(
        id="dev-seed-timeline-main",
        project_id=project_main.id,
        name="30 秒 TikTok 竖版成片",
        status="draft",
        duration_seconds=30.0,
        tracks_json=_json({"video": ["s1", "s2", "s3"], "voice": ["voice-main"], "subtitle": ["subtitle-main"]}),
        source=DEV_SEED_SOURCE,
        created_at=now,
        updated_at=now,
    )
    session.add(timeline)
    session.flush()
    session.add_all(
        [
            VoiceTrack(
                id="dev-seed-voice-main",
                project_id=project_main.id,
                timeline_id=timeline.id,
                source=DEV_SEED_SOURCE,
                provider="openai",
                voice_name="清晰女声 / 中文",
                file_path=None,
                segments_json=_json([{"start": 0, "end": 10, "text": "开头抓痛点"}, {"start": 10, "end": 30, "text": "展示闭环"}]),
                status="ready",
                created_at=now,
            ),
            SubtitleTrack(
                id="dev-seed-subtitle-main",
                project_id=project_main.id,
                timeline_id=timeline.id,
                source=DEV_SEED_SOURCE,
                language="zh-CN",
                style_json=_json({"template": "tiktok-bold", "position": "bottom"}),
                segments_json=_json([{"start": 0, "end": 3, "text": "素材太多剪不完？"}, {"start": 3, "end": 30, "text": "交给 AI 创作中枢串起来。"}]),
                status="aligned",
                created_at=now,
            ),
            RenderTask(
                id="dev-seed-render-main",
                project_id=project_main.id,
                timeline_id=timeline.id,
                status="queued",
                output_path=str(Path(".runtime-data") / "exports" / "dev-seed-tiktok-demo.mp4"),
                profile_json=_json({"format": "mp4", "resolution": "1080x1920", "fps": 30}),
                progress=0,
                source=DEV_SEED_SOURCE,
                error_message=None,
                created_at=now,
                updated_at=now,
            ),
        ]
    )

    account = Account(
        id="dev-seed-account-tiktok-main",
        platform="tiktok",
        handle="@tkops_demo",
        display_name="TK-OPS 测试账号",
        group_name="开发样例组",
        status="healthy",
        source=DEV_SEED_SOURCE,
        metadata_json=_json({"region": "US", "note": "仅用于本地开发调试"}),
        created_at=now,
    )
    workspace = DeviceWorkspace(
        id="dev-seed-device-local-browser",
        name="本机 Chrome 工作区",
        device_type="pc_browser",
        root_path=str(Path.home()),
        browser_profile="Default",
        status="ready",
        health_json=_json({"disk": "ok", "browser": "configured"}),
        source=DEV_SEED_SOURCE,
        created_at=now,
    )
    binding = ExecutionBinding(
        id="dev-seed-binding-main",
        account_id=account.id,
        device_workspace_id=workspace.id,
        status="active",
        source=DEV_SEED_SOURCE,
        metadata_json=_json({"policy": "manual_review_before_publish"}),
        created_at=now,
    )
    session.add_all([account, workspace])
    session.flush()
    session.add(binding)
    session.flush()
    session.add_all(
        [
            PublishPlan(
                id="dev-seed-publish-main",
                project_id=project_main.id,
                account_id=account.id,
                binding_id=binding.id,
                status="scheduled",
                scheduled_at=later,
                caption="用 AI 把脚本、分镜、配音、字幕和发布串成一个闭环。",
                source=DEV_SEED_SOURCE,
                metadata_json=_json({"hashtags": ["#AIVideo", "#TikTokCreator"]}),
                created_at=now,
            ),
            AutomationTask(
                id="dev-seed-automation-publish-check",
                project_id=project_main.id,
                binding_id=binding.id,
                task_type="publish",
                status="waiting",
                schedule_json=_json({"mode": "manual_window", "scheduledAt": later}),
                payload_json=_json({"publishPlanId": "dev-seed-publish-main"}),
                source=DEV_SEED_SOURCE,
                created_at=now,
                updated_at=now,
            ),
            AutomationTask(
                id="dev-seed-automation-sync-check",
                project_id=project_import.id,
                binding_id=binding.id,
                task_type="sync_check",
                status="queued",
                schedule_json=_json({"mode": "on_demand"}),
                payload_json=_json({"scope": "asset_index"}),
                source=DEV_SEED_SOURCE,
                created_at=now,
                updated_at=now,
            ),
        ]
    )

    _insert_assets_and_imported_videos(session, candidates, project_import.id, now)


def _insert_assets_and_imported_videos(
    session: Session,
    candidates: Sequence[LocalAssetCandidate],
    project_id: str,
    now: str,
) -> None:
    for index, candidate in enumerate(candidates, start=1):
        asset_id = f"dev-seed-asset-{index:03d}"
        session.add(
            Asset(
                id=asset_id,
                project_id=project_id,
                kind=candidate.kind,
                file_path=str(candidate.path),
                file_name=candidate.file_name,
                file_size_bytes=candidate.file_size_bytes,
                mime_type=candidate.mime_type,
                source=DEV_SEED_SOURCE,
                metadata_json=_json(
                    {
                        "source": DEV_SEED_SOURCE,
                        "modifiedAt": candidate.modified_at,
                        "copied": False,
                    }
                ),
                created_at=now,
            )
        )
        if candidate.kind == "video":
            session.add(
                ImportedVideo(
                    id=f"dev-seed-imported-video-{index:03d}",
                    project_id=project_id,
                    file_path=str(candidate.path),
                    file_name=candidate.file_name,
                    file_size_bytes=candidate.file_size_bytes,
                    duration_seconds=None,
                    width=None,
                    height=None,
                    frame_rate=None,
                    codec=None,
                    status="indexed",
                    error_message="开发种子仅索引本机路径，未执行 FFprobe。",
                    created_at=now,
                )
            )


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
