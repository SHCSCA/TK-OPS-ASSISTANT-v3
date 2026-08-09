from __future__ import annotations

from pathlib import Path
import tomllib

import pytest

from domain.models.account_configuration import AccountPublishDefaults
from errors import DomainError
from schemas.v1.account_configuration import (
    BrandKitVersionInput,
    PositioningVersionInput,
    PublishDefaultsInput,
)
from services.accounts.branding import (
    _publish_defaults_to_dto,
    _validate_brand_kit,
    _validate_publish_defaults,
)
from services.accounts.positioning import _validate_positioning


def test_runtime_declares_cross_platform_iana_timezone_data() -> None:
    runtime_root = Path(__file__).resolve().parents[2] / "apps" / "py-runtime"
    project = tomllib.loads(
        (runtime_root / "pyproject.toml").read_text(encoding="utf-8")
    )
    dependencies = project["project"]["dependencies"]

    assert any(
        dependency.partition(">=")[0].strip().lower() == "tzdata"
        for dependency in dependencies
    )


def test_positioning_rejects_blank_duplicate_pillars() -> None:
    payload = PositioningVersionInput(
        audience={"market": "北美"},
        contentPillars=["效率", " 效率 "],
        tone={"style": "清晰"},
        prohibitedTopics=[],
        publishingConstraints={},
    )

    with pytest.raises(DomainError) as exc_info:
        _validate_positioning(payload)

    assert exc_info.value.error_code == "POSITIONING_INVALID"
    assert exc_info.value.status_code == 422


def test_brand_kit_rejects_paths_and_invalid_colors() -> None:
    payload = BrandKitVersionInput(
        colors=["blue"],
        fonts=["Inter"],
        logoAssetRefs=["C:\\secret\\logo.png"],
        visualRules={},
        voiceRules={},
    )

    with pytest.raises(DomainError) as exc_info:
        _validate_brand_kit(payload)

    assert exc_info.value.error_code == "BRAND_KIT_INVALID"
    assert {
        item.field for item in exc_info.value.field_errors
    } == {"colors", "logoAssetRefs"}


def test_publish_defaults_use_real_timezone_and_platform_rules() -> None:
    valid = PublishDefaultsInput(
        timezone="Asia/Shanghai",
        privacyLevel="PUBLIC",
        allowComments=True,
        allowDuet=True,
        allowStitch=True,
        captionRules={},
    )

    assert _validate_publish_defaults(valid) == (
        "Asia/Shanghai",
        "public",
    )

    invalid = valid.model_copy(
        update={
            "timezone": "Mars/Base",
            "privacyLevel": "private",
            "allowDuet": True,
        }
    )
    with pytest.raises(DomainError) as exc_info:
        _validate_publish_defaults(invalid)

    assert exc_info.value.error_code == "PUBLISH_DEFAULTS_INVALID"
    assert exc_info.value.status_code == 422


def test_publish_defaults_dto_exposes_account_aggregate_revision() -> None:
    stored = AccountPublishDefaults(
        account_id="account-a",
        timezone="UTC",
        privacy_level="private",
        allow_comments=False,
        allow_duet=False,
        allow_stitch=False,
        caption_rules_json="{}",
        revision=3,
        created_at="2026-07-26T00:00:00Z",
        updated_at="2026-07-26T00:00:00Z",
    )

    dto = _publish_defaults_to_dto(stored, account_revision=11)

    assert dto.revision == 11
