from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING

from common.http_errors import RuntimeHTTPException
from common.time import utc_now_iso
from domain.models.magic_cut import MagicCutSuggestionDraft
from domain.models.timeline import Timeline
from repositories.magic_cut_repository import MagicCutSuggestionRepository
from repositories.timeline_repository import TimelineRepository
from schemas.workspace import MagicCutSuggestionDraftDto, MagicCutSuggestionOperationDto
from services.magic_cut import apply_magic_cut_operations

if TYPE_CHECKING:
    from services.workspace_service import WorkspaceService

log = logging.getLogger(__name__)

NOT_FOUND_CODE = "workspace.magic_cut_suggestion_not_found"
TIMELINE_CHANGED_CODE = "workspace.magic_cut_timeline_changed"
APPLY_FAILED_CODE = "workspace.magic_cut_apply_failed"
NOT_REVIEWABLE_CODE = "workspace.magic_cut_suggestion_not_reviewable"
INVALID_OPERATION_CODE = "workspace.magic_cut_invalid_operation"

NOT_FOUND_MESSAGE = "智能粗剪建议不存在，请重新生成。"
TIMELINE_CHANGED_MESSAGE = "时间线已变化，请重新生成智能粗剪建议。"
APPLY_FAILED_MESSAGE = "应用失败，已保留原时间线。"
NOT_REVIEWABLE_MESSAGE = "当前建议已处理，请重新生成。"
INVALID_OPERATION_MESSAGE = "智能粗剪建议内容无效，请重新生成。"
FAILED_PARSE_MESSAGE = "AI 返回内容无法生成建议，请重新生成。"


def build_timeline_version_token(timeline: Timeline) -> str:
    payload = {
        "timelineId": timeline.id,
        "updatedAt": timeline.updated_at,
        "tracksJson": timeline.tracks_json,
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"sha256:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"


class MagicCutSuggestionService:
    def __init__(
        self,
        repository: MagicCutSuggestionRepository,
        timeline_repository: TimelineRepository,
    ) -> None:
        self._repository = repository
        self._timeline_repository = timeline_repository

    def create_from_operations(
        self,
        project_id: str,
        timeline: Timeline,
        operations: list[dict[str, object]],
        summary: str,
        ai_job_id: str | None,
    ) -> MagicCutSuggestionDraftDto:
        try:
            normalized = self._normalize_operations(timeline, operations)
            if not normalized:
                return self.create_failed_parse(project_id, timeline, FAILED_PARSE_MESSAGE, ai_job_id)

            draft = self._repository.create_pending(
                project_id,
                timeline.id,
                summary.strip() or "已生成智能粗剪建议。",
                json.dumps(normalized, ensure_ascii=False),
                build_timeline_version_token(timeline),
                ai_job_id,
            )
            return self.to_dto(draft)
        except Exception:
            log.exception("智能粗剪建议保存失败")
            raise

    def create_failed_parse(
        self,
        project_id: str,
        timeline: Timeline,
        summary: str,
        ai_job_id: str | None,
    ) -> MagicCutSuggestionDraftDto:
        try:
            draft = self._repository.create_failed_parse(
                project_id,
                timeline.id,
                summary.strip() or FAILED_PARSE_MESSAGE,
                build_timeline_version_token(timeline),
                ai_job_id,
            )
            return self.to_dto(draft)
        except Exception:
            log.exception("智能粗剪建议保存失败")
            raise

    def latest(self, project_id: str, timeline_id: str) -> MagicCutSuggestionDraftDto | None:
        draft = self._repository.get_latest(project_id, timeline_id)
        if draft is None:
            return None
        return self.to_dto(draft)

    def dismiss(self, suggestion_id: str) -> MagicCutSuggestionDraftDto:
        draft = self._repository.get_by_id(suggestion_id)
        if draft is None:
            self._raise_not_found()
        dismissed = self._repository.mark_dismissed(suggestion_id)
        if dismissed is None:
            self._raise_not_found()
        return self.to_dto(dismissed)

    def apply(
        self,
        suggestion_id: str,
        operation_ids: list[str],
        confirm_timeline_version_token: str,
        workspace_service: WorkspaceService,
    ) -> tuple[MagicCutSuggestionDraftDto, Timeline, int]:
        draft = self._repository.get_by_id(suggestion_id)
        if draft is None:
            self._raise_not_found()
        if draft.status != "pending_review":
            raise RuntimeHTTPException(
                status_code=409,
                detail=NOT_REVIEWABLE_MESSAGE,
                error_code=NOT_REVIEWABLE_CODE,
            )

        timeline = self._timeline_repository.get_by_id(draft.timeline_id)
        if timeline is None:
            self._raise_not_found()

        current_token = build_timeline_version_token(timeline)
        if (
            confirm_timeline_version_token != draft.timeline_version_token
            or current_token != draft.timeline_version_token
        ):
            log.warning(
                "智能粗剪建议应用被拒绝 timeline_changed suggestion_id=%s timeline_id=%s",
                suggestion_id,
                draft.timeline_id,
            )
            raise RuntimeHTTPException(
                status_code=409,
                detail=TIMELINE_CHANGED_MESSAGE,
                error_code=TIMELINE_CHANGED_CODE,
            )

        operations = self._load_operations(draft)
        selected = self._select_operations(operations, operation_ids)
        snapshot = {
            "tracks_json": timeline.tracks_json,
            "duration_seconds": timeline.duration_seconds,
            "status": timeline.status,
            "updated_at": timeline.updated_at,
        }

        try:
            applied, failed, message = apply_magic_cut_operations(
                workspace_service,
                timeline.id,
                [self._to_apply_operation(operation) for operation in selected],
            )
            if failed > 0 or applied != len(selected):
                raise RuntimeError(message)
        except Exception as exc:
            self._timeline_repository.restore_snapshot(
                timeline.id,
                tracks_json=str(snapshot["tracks_json"]),
                duration_seconds=snapshot["duration_seconds"],  # type: ignore[arg-type]
                status=str(snapshot["status"]),
                updated_at=str(snapshot["updated_at"]),
            )
            log.exception("智能粗剪建议应用失败")
            raise RuntimeHTTPException(
                status_code=409,
                detail=APPLY_FAILED_MESSAGE,
                error_code=APPLY_FAILED_CODE,
            ) from exc

        applied_at = utc_now_iso()
        applied_draft = self._repository.mark_applied(suggestion_id, applied_at)
        if applied_draft is None:
            self._raise_not_found()
        updated_timeline = self._timeline_repository.get_by_id(timeline.id)
        if updated_timeline is None:
            self._raise_not_found()
        return self.to_dto(applied_draft), updated_timeline, applied

    def to_dto(self, draft: MagicCutSuggestionDraft) -> MagicCutSuggestionDraftDto:
        return MagicCutSuggestionDraftDto(
            id=draft.id,
            projectId=draft.project_id,
            timelineId=draft.timeline_id,
            timelineVersionToken=draft.timeline_version_token,
            status=draft.status,
            summary=draft.summary,
            operations=[
                MagicCutSuggestionOperationDto.model_validate(operation)
                for operation in self._load_operations(draft)
            ],
            createdAt=draft.created_at,
            updatedAt=draft.updated_at,
            appliedAt=draft.applied_at,
        )

    def _normalize_operations(
        self,
        timeline: Timeline,
        operations: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        clips = self._index_timeline_clips(timeline)
        normalized: list[dict[str, object]] = []
        for index, operation in enumerate(operations, start=1):
            action = str(operation.get("action") or "").strip().lower()
            clip_id = str(operation.get("clipId") or "").strip()
            if action not in {"delete", "trim", "move", "split"} or clip_id not in clips:
                log.warning("智能粗剪建议包含不可审阅操作 action=%s clip_id=%s", action, clip_id)
                continue

            clip = clips[clip_id]
            item: dict[str, object] = {
                "id": f"suggestion-{action}-{clip_id}-{index}",
                "action": action,
                "clipId": clip_id,
                "trackId": str(clip.get("trackId") or ""),
                "originalStartMs": int(clip.get("startMs") or 0),
                "originalDurationMs": int(clip.get("durationMs") or 0),
                "reason": str(operation.get("reason") or "AI 建议优化该片段节奏。"),
                "risk": None,
            }
            if action == "delete":
                item["risk"] = "删除片段会移除当前素材。"
            elif action == "trim":
                item["suggestedStartMs"] = int(operation.get("startMs") or 0)
                item["suggestedDurationMs"] = int(operation.get("durationMs") or 0)
            elif action == "move":
                item["suggestedStartMs"] = int(operation.get("startMs") or 0)
                item["targetTrackId"] = str(operation.get("targetTrackId") or "")
                item["risk"] = "移动片段可能影响同轨节奏。"
            elif action == "split":
                item["splitAtMs"] = int(operation.get("splitAtMs") or 0)
            normalized.append(item)
        return normalized

    def _index_timeline_clips(self, timeline: Timeline) -> dict[str, dict[str, object]]:
        try:
            tracks = json.loads(timeline.tracks_json)
        except (TypeError, ValueError):
            log.exception("解析智能粗剪建议时间线失败")
            return {}
        if not isinstance(tracks, list):
            return {}
        clips: dict[str, dict[str, object]] = {}
        for track in tracks:
            if not isinstance(track, dict):
                continue
            for clip in track.get("clips") or []:
                if not isinstance(clip, dict):
                    continue
                clip_id = str(clip.get("id") or "")
                if clip_id:
                    clips[clip_id] = clip
        return clips

    def _load_operations(self, draft: MagicCutSuggestionDraft) -> list[dict[str, object]]:
        try:
            decoded = json.loads(draft.operations_json)
        except (TypeError, ValueError) as exc:
            log.exception("解析智能粗剪建议 JSON 失败")
            raise RuntimeHTTPException(
                status_code=400,
                detail=INVALID_OPERATION_MESSAGE,
                error_code=INVALID_OPERATION_CODE,
            ) from exc
        if not isinstance(decoded, list):
            raise RuntimeHTTPException(
                status_code=400,
                detail=INVALID_OPERATION_MESSAGE,
                error_code=INVALID_OPERATION_CODE,
            )
        return [item for item in decoded if isinstance(item, dict)]

    def _select_operations(
        self,
        operations: list[dict[str, object]],
        operation_ids: list[str],
    ) -> list[dict[str, object]]:
        if len(operation_ids) != len(set(operation_ids)):
            self._raise_invalid_operation()
        by_id = {str(operation.get("id") or ""): operation for operation in operations}
        if not operation_ids:
            selected = operations
        else:
            selected = []
            for operation_id in operation_ids:
                operation = by_id.get(operation_id)
                if operation is None:
                    self._raise_invalid_operation()
                selected.append(operation)
        if not selected:
            self._raise_invalid_operation()
        for operation in selected:
            self._validate_operation(operation)
        return selected

    def _validate_operation(self, operation: dict[str, object]) -> None:
        action = str(operation.get("action") or "")
        clip_id = str(operation.get("clipId") or "")
        if not clip_id:
            self._raise_invalid_operation()
        if action == "delete":
            return
        if action == "trim":
            if operation.get("suggestedStartMs") is None or operation.get("suggestedDurationMs") is None:
                self._raise_invalid_operation()
            return
        if action == "move":
            if operation.get("suggestedStartMs") is None or not str(operation.get("targetTrackId") or ""):
                self._raise_invalid_operation()
            return
        if action == "split":
            if operation.get("splitAtMs") is None:
                self._raise_invalid_operation()
            return
        self._raise_invalid_operation()

    def _to_apply_operation(self, operation: dict[str, object]) -> dict[str, object]:
        action = str(operation.get("action") or "")
        payload: dict[str, object] = {
            "action": action,
            "clipId": str(operation.get("clipId") or ""),
        }
        if action == "trim":
            payload["startMs"] = int(operation.get("suggestedStartMs") or 0)
            payload["durationMs"] = int(operation.get("suggestedDurationMs") or 0)
        elif action == "move":
            payload["startMs"] = int(operation.get("suggestedStartMs") or 0)
            payload["targetTrackId"] = str(operation.get("targetTrackId") or "")
        elif action == "split":
            payload["splitAtMs"] = int(operation.get("splitAtMs") or 0)
        return payload

    def _raise_not_found(self) -> None:
        raise RuntimeHTTPException(
            status_code=404,
            detail=NOT_FOUND_MESSAGE,
            error_code=NOT_FOUND_CODE,
        )

    def _raise_invalid_operation(self) -> None:
        raise RuntimeHTTPException(
            status_code=400,
            detail=INVALID_OPERATION_MESSAGE,
            error_code=INVALID_OPERATION_CODE,
        )
