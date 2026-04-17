from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def _assert_ok(payload: dict[str, object]) -> object:
    assert set(payload) == {"ok", "data"}
    assert payload["ok"] is True
    return payload["data"]


def _create_project(runtime_client: TestClient, name: str = "Gap Closure Project") -> str:
    response = runtime_client.post(
        "/api/dashboard/projects",
        json={"name": name, "description": "contract coverage"},
    )
    assert response.status_code == 200
    return _assert_ok(response.json())["id"]


def _create_account(runtime_client: TestClient, name: str = "Creator A") -> str:
    response = runtime_client.post(
        "/api/accounts",
        json={"name": name, "platform": "tiktok", "username": "creator_a"},
    )
    assert response.status_code == 200
    return _assert_ok(response.json())["id"]


def _create_workspace(runtime_client: TestClient, root_path: str) -> str:
    response = runtime_client.post(
        "/api/devices/workspaces",
        json={"name": "Main Workspace", "root_path": root_path},
    )
    assert response.status_code == 201
    return _assert_ok(response.json())["id"]


def _import_video(runtime_client: TestClient, project_id: str, video_path: Path) -> str:
    with patch("tasks.video_tasks.probe_video", return_value=None):
        response = runtime_client.post(
            f"/api/video-deconstruction/projects/{project_id}/import",
            json={"filePath": str(video_path)},
        )
    assert response.status_code == 200
    return _assert_ok(response.json())["id"]


def test_accounts_status_check_alias_matches_refresh_stats(runtime_client: TestClient) -> None:
    account_id = _create_account(runtime_client)

    refresh_response = runtime_client.post(f"/api/accounts/{account_id}/refresh-stats")
    assert refresh_response.status_code == 200
    refresh_data = _assert_ok(refresh_response.json())

    alias_response = runtime_client.post(f"/api/accounts/{account_id}/status-check")
    assert alias_response.status_code == 200
    alias_data = _assert_ok(alias_response.json())

    assert set(alias_data) == {"id", "status", "updatedAt", "providerStatus"}
    assert alias_data["id"] == refresh_data["id"] == account_id
    assert alias_data["status"] == refresh_data["status"]


def test_devices_contract_covers_browser_instances_and_bindings(
    runtime_client: TestClient,
    tmp_path: Path,
) -> None:
    workspace_id = _create_workspace(runtime_client, str(tmp_path / "workspace-a"))
    account_id = _create_account(runtime_client)

    browser_response = runtime_client.post(
        "/api/devices/browser-instances",
        json={
            "workspace_id": workspace_id,
            "name": "Chrome Main",
            "profile_path": str(tmp_path / "profiles" / "chrome-main"),
            "browser_type": "chrome",
        },
    )
    assert browser_response.status_code == 201
    browser_instance = _assert_ok(browser_response.json())
    assert set(browser_instance) == {
        "id",
        "workspace_id",
        "name",
        "profile_path",
        "browser_type",
        "status",
        "last_seen_at",
        "created_at",
        "updated_at",
    }

    list_browser_response = runtime_client.get(
        f"/api/devices/browser-instances?workspace_id={workspace_id}"
    )
    assert list_browser_response.status_code == 200
    listed_browser_instances = _assert_ok(list_browser_response.json())
    assert listed_browser_instances[0]["id"] == browser_instance["id"]

    binding_response = runtime_client.post(
        "/api/devices/bindings",
        json={
            "account_id": account_id,
            "device_workspace_id": workspace_id,
            "browser_instance_id": browser_instance["id"],
            "source": "publish",
        },
    )
    assert binding_response.status_code == 201
    binding = _assert_ok(binding_response.json())
    assert set(binding) == {
        "id",
        "account_id",
        "device_workspace_id",
        "browser_instance_id",
        "status",
        "source",
        "metadata_json",
        "created_at",
        "updated_at",
    }

    list_bindings_response = runtime_client.get(
        f"/api/devices/bindings?device_workspace_id={workspace_id}"
    )
    assert list_bindings_response.status_code == 200
    listed_bindings = _assert_ok(list_bindings_response.json())
    assert listed_bindings[0]["id"] == binding["id"]

    blocked_delete_response = runtime_client.delete(
        f"/api/devices/browser-instances/{browser_instance['id']}"
    )
    assert blocked_delete_response.status_code == 409
    blocked_payload = blocked_delete_response.json()
    assert blocked_payload["ok"] is False
    assert "绑定" in blocked_payload["error"]

    delete_binding_response = runtime_client.delete(f"/api/devices/bindings/{binding['id']}")
    assert delete_binding_response.status_code == 200
    assert _assert_ok(delete_binding_response.json()) == {"deleted": True}

    delete_browser_response = runtime_client.delete(
        f"/api/devices/browser-instances/{browser_instance['id']}"
    )
    assert delete_browser_response.status_code == 200
    assert _assert_ok(delete_browser_response.json()) == {"deleted": True}


def test_automation_contract_covers_run_detail_cancel_and_logs(
    runtime_client: TestClient,
) -> None:
    create_response = runtime_client.post(
        "/api/automation/tasks",
        json={"name": "同步发布状态", "type": "sync_status"},
    )
    assert create_response.status_code == 201
    task_id = _assert_ok(create_response.json())["id"]

    trigger_response = runtime_client.post(f"/api/automation/tasks/{task_id}/trigger")
    assert trigger_response.status_code == 200
    trigger_data = _assert_ok(trigger_response.json())
    run_id = trigger_data["run_id"]

    run_detail_response = runtime_client.get(f"/api/automation/runs/{run_id}")
    assert run_detail_response.status_code == 200
    run_detail = _assert_ok(run_detail_response.json())
    assert set(run_detail) == {
        "id",
        "task_id",
        "status",
        "started_at",
        "finished_at",
        "log_text",
        "created_at",
    }

    logs_response = runtime_client.get(f"/api/automation/runs/{run_id}/logs")
    assert logs_response.status_code == 200
    logs = _assert_ok(logs_response.json())
    assert set(logs) == {"run_id", "log_text", "lines"}
    assert logs["run_id"] == run_id
    assert isinstance(logs["lines"], list)

    cancel_response = runtime_client.post(f"/api/automation/runs/{run_id}/cancel")
    assert cancel_response.status_code == 200
    cancelled_run = _assert_ok(cancel_response.json())
    assert cancelled_run["id"] == run_id
    assert cancelled_run["status"] == "cancelled"


def test_publishing_contract_covers_receipt(runtime_client: TestClient) -> None:
    plan_response = runtime_client.post(
        "/api/publishing/plans",
        json={"title": "发布计划 A", "account_name": "Creator A", "project_id": "project-1"},
    )
    assert plan_response.status_code == 201
    plan_id = _assert_ok(plan_response.json())["id"]

    precheck_response = runtime_client.post(f"/api/publishing/plans/{plan_id}/precheck")
    assert precheck_response.status_code == 200
    assert _assert_ok(precheck_response.json())["has_errors"] is False

    submit_response = runtime_client.post(f"/api/publishing/plans/{plan_id}/submit")
    assert submit_response.status_code == 200
    assert _assert_ok(submit_response.json())["status"] == "submitted"

    receipt_response = runtime_client.get(f"/api/publishing/plans/{plan_id}/receipt")
    assert receipt_response.status_code == 200
    receipt = _assert_ok(receipt_response.json())
    assert set(receipt) == {
        "id",
        "plan_id",
        "status",
        "external_url",
        "error_message",
        "completed_at",
        "created_at",
    }
    assert receipt["plan_id"] == plan_id
    assert receipt["status"] == "manual_required"


def test_renders_contract_covers_profiles_and_retry(runtime_client: TestClient) -> None:
    profiles_response = runtime_client.get("/api/renders/profiles")
    assert profiles_response.status_code == 200
    profiles = _assert_ok(profiles_response.json())
    assert len(profiles) >= 1
    assert profiles[0]["is_default"] is True

    create_profile_response = runtime_client.post(
        "/api/renders/profiles",
        json={
            "name": "竖屏高码率",
            "format": "mp4",
            "resolution": "1080x1920",
            "fps": 30,
            "video_bitrate": "12000k",
            "audio_policy": "merge_all",
            "subtitle_policy": "burn_in",
        },
    )
    assert create_profile_response.status_code == 201
    profile = _assert_ok(create_profile_response.json())
    assert profile["name"] == "竖屏高码率"

    create_task_response = runtime_client.post(
        "/api/renders/tasks",
        json={"project_id": "project-1", "project_name": "Demo", "preset": "1080p"},
    )
    assert create_task_response.status_code == 201
    task_id = _assert_ok(create_task_response.json())["id"]

    fail_task_response = runtime_client.patch(
        f"/api/renders/tasks/{task_id}",
        json={"status": "failed", "progress": 100, "error_message": "编码失败"},
    )
    assert fail_task_response.status_code == 200
    assert _assert_ok(fail_task_response.json())["status"] == "failed"

    retry_response = runtime_client.post(f"/api/renders/tasks/{task_id}/retry")
    assert retry_response.status_code == 200
    retried_task = _assert_ok(retry_response.json())
    assert retried_task["id"] == task_id
    assert retried_task["status"] == "queued"
    assert retried_task["progress"] == 0
    assert retried_task["error_message"] is None


def test_review_contract_covers_suggestions_and_apply_to_script(
    runtime_client: TestClient,
) -> None:
    project_id = _create_project(runtime_client, name="Review Project")

    generate_response = runtime_client.post(
        f"/api/review/projects/{project_id}/suggestions/generate"
    )
    assert generate_response.status_code == 200
    generate_result = _assert_ok(generate_response.json())
    assert set(generate_result) == {
        "project_id",
        "status",
        "message",
        "generated_count",
        "generated_at",
    }
    assert generate_result["generated_count"] >= 1

    list_response = runtime_client.get(f"/api/review/projects/{project_id}/suggestions")
    assert list_response.status_code == 200
    suggestions = _assert_ok(list_response.json())
    assert len(suggestions) >= 1
    suggestion_id = suggestions[0]["id"]
    assert set(suggestions[0]) == {
        "id",
        "code",
        "category",
        "title",
        "description",
        "priority",
        "status",
        "actionLabel",
        "sourceType",
        "sourceId",
        "createdAt",
    }

    patch_response = runtime_client.patch(
        f"/api/review/suggestions/{suggestion_id}",
        json={"status": "dismissed"},
    )
    assert patch_response.status_code == 200
    assert _assert_ok(patch_response.json())["status"] == "dismissed"

    apply_response = runtime_client.post(
        f"/api/review/suggestions/{suggestion_id}/apply-to-script"
    )
    assert apply_response.status_code == 200
    apply_result = _assert_ok(apply_response.json())
    assert set(apply_result) == {
        "project_id",
        "suggestion_id",
        "script_revision",
        "status",
        "message",
    }
    assert apply_result["status"] == "applied"
    assert apply_result["script_revision"] == 1


def test_video_deconstruction_contract_covers_new_interfaces(
    runtime_client: TestClient,
    tmp_path: Path,
) -> None:
    project_id = _create_project(runtime_client, name="Video Project")
    video_path = tmp_path / "deconstruction.mp4"
    video_path.write_bytes(b"\x00" * 2048)
    video_id = _import_video(runtime_client, project_id, video_path)

    transcribe_response = runtime_client.post(
        f"/api/video-deconstruction/videos/{video_id}/transcribe"
    )
    assert transcribe_response.status_code == 200
    transcript = _assert_ok(transcribe_response.json())
    assert set(transcript) == {
        "id",
        "videoId",
        "language",
        "text",
        "status",
        "createdAt",
        "updatedAt",
    }
    assert transcript["status"] == "pending_provider"
    assert transcript["text"] is None

    get_transcript_response = runtime_client.get(
        f"/api/video-deconstruction/videos/{video_id}/transcript"
    )
    assert get_transcript_response.status_code == 200
    assert _assert_ok(get_transcript_response.json())["id"] == transcript["id"]

    segment_response = runtime_client.post(f"/api/video-deconstruction/videos/{video_id}/segment")
    assert segment_response.status_code == 200
    segments = _assert_ok(segment_response.json())
    assert len(segments) >= 1
    assert set(segments[0]) == {
        "id",
        "videoId",
        "segmentIndex",
        "startMs",
        "endMs",
        "label",
        "transcriptText",
        "metadataJson",
        "createdAt",
    }

    list_segments_response = runtime_client.get(
        f"/api/video-deconstruction/videos/{video_id}/segments"
    )
    assert list_segments_response.status_code == 200
    assert len(_assert_ok(list_segments_response.json())) == len(segments)

    extract_response = runtime_client.post(
        f"/api/video-deconstruction/videos/{video_id}/extract-structure"
    )
    assert extract_response.status_code == 200
    extraction = _assert_ok(extract_response.json())
    assert set(extraction) == {
        "id",
        "videoId",
        "status",
        "scriptJson",
        "storyboardJson",
        "createdAt",
        "updatedAt",
    }

    structure_response = runtime_client.get(
        f"/api/video-deconstruction/videos/{video_id}/structure"
    )
    assert structure_response.status_code == 200
    assert _assert_ok(structure_response.json())["id"] == extraction["id"]

    apply_response = runtime_client.post(
        f"/api/video-deconstruction/extractions/{extraction['id']}/apply-to-project"
    )
    assert apply_response.status_code == 409
    apply_payload = apply_response.json()
    assert apply_payload["ok"] is False
    assert "转写" in apply_payload["error"] or "结构" in apply_payload["error"]
