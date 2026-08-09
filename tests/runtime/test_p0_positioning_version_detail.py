from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from domain.models.account_configuration import PositioningProfile
from errors import ErrorCode
from tests.runtime.p0c_account_integration_support import (
    create_account,
    error_code,
    mutation_headers,
    session,
)


def test_positioning_detail_is_account_scoped_and_hides_missing_versions(
    licensed_runtime_client: TestClient,
) -> None:
    client = licensed_runtime_client
    account_a, revision_a = create_account(
        client,
        name="定位详情 A",
        idempotency_key="idem_positioning_detail_account_a",
    )
    account_b, revision_b = create_account(
        client,
        name="定位详情 B",
        idempotency_key="idem_positioning_detail_account_b",
    )
    _create_positioning(
        client,
        account_id=account_a,
        revision=revision_a,
        audience="准备出海的独立开发者",
        pillars=["产品拆解", "增长实验"],
        idempotency_key="idem_positioning_detail_a_v1",
    )
    _create_positioning(
        client,
        account_id=account_b,
        revision=revision_b,
        audience="北美健身爱好者",
        pillars=["训练计划"],
        idempotency_key="idem_positioning_detail_b_v1",
    )

    detail_a = client.get(
        f"/api/v1/accounts/{account_a}/positioning/versions/1"
    )
    detail_b = client.get(
        f"/api/v1/accounts/{account_b}/positioning/versions/1"
    )
    missing = client.get(
        f"/api/v1/accounts/{account_a}/positioning/versions/2"
    )

    assert detail_a.status_code == 200, detail_a.text
    assert detail_b.status_code == 200, detail_b.text
    assert detail_a.json()["data"]["accountId"] == account_a
    assert detail_a.json()["data"]["audience"]["description"] == (
        "准备出海的独立开发者"
    )
    assert detail_b.json()["data"]["accountId"] == account_b
    assert detail_b.json()["data"]["audience"]["description"] == (
        "北美健身爱好者"
    )
    assert missing.status_code == 404
    assert error_code(missing) == ErrorCode.POSITIONING_VERSION_NOT_FOUND


def test_positioning_summary_is_derived_for_new_and_legacy_rows(
    licensed_runtime_client: TestClient,
) -> None:
    client = licensed_runtime_client
    account_id, revision = create_account(
        client,
        name="定位摘要兼容",
        idempotency_key="idem_positioning_summary_account",
    )
    created = _create_positioning(
        client,
        account_id=account_id,
        revision=revision,
        audience="准备出海的独立开发者",
        pillars=["产品拆解", "增长实验", "AI 工作流", "工具评测"],
        idempotency_key="idem_positioning_summary_v1",
    )

    assert created["summary"].startswith("面向准备出海的独立开发者")
    assert "产品拆解 / 增长实验 / AI 工作流" in created["summary"]
    assert "等 4 个方向" in created["summary"]

    with session(client) as database:
        profile = database.scalar(
            select(PositioningProfile).where(
                PositioningProfile.account_id == account_id,
                PositioningProfile.version == 1,
            )
        )
        assert profile is not None
        profile.summary = "已配置 4 个内容支柱"
        database.commit()

    collection = client.get(
        f"/api/v1/accounts/{account_id}/positioning"
    )
    detail = client.get(
        f"/api/v1/accounts/{account_id}/positioning/versions/1"
    )

    assert collection.status_code == 200, collection.text
    assert detail.status_code == 200, detail.text
    collection_summary = collection.json()["data"]["versions"][0]["summary"]
    detail_summary = detail.json()["data"]["summary"]
    assert collection_summary == detail_summary
    assert collection_summary.startswith("面向准备出海的独立开发者")

    with session(client) as database:
        stored = database.scalar(
            select(PositioningProfile).where(
                PositioningProfile.account_id == account_id,
                PositioningProfile.version == 1,
            )
        )
        assert stored is not None
        assert stored.summary == "已配置 4 个内容支柱"


def _create_positioning(
    client: TestClient,
    *,
    account_id: str,
    revision: int,
    audience: str,
    pillars: list[str],
    idempotency_key: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/accounts/{account_id}/positioning/versions",
        headers=mutation_headers(
            revision=revision,
            idempotency_key=idempotency_key,
        ),
        json={
            "audience": {"description": audience},
            "contentPillars": pillars,
            "tone": {"description": "直接、克制、有证据"},
            "prohibitedTopics": ["未经验证的收益承诺"],
            "publishingConstraints": {
                "description": "结论必须附带来源"
            },
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]
