from __future__ import annotations

from collections.abc import Mapping

from domain.models.ai_configuration_v1 import CompositionTemplateProfile
from services.ai_execution_v1.dependency_graph import DependencyResolution

from .dependency_snapshots import validation_resolution
from .template_validation import _template_validation
from .unit_of_work import AIConfigurationTransaction


def resolve_template_dependencies(
    transaction: AIConfigurationTransaction,
    row: CompositionTemplateProfile,
    *,
    validation: Mapping[str, object] | None = None,
) -> DependencyResolution:
    result = dict(validation or _template_validation(transaction, row))
    raw_issues = result.get("validationIssues")
    issues = (
        tuple(item for item in raw_issues if isinstance(item, Mapping))
        if isinstance(raw_issues, list)
        else ()
    )
    verified = result.get("verifiedCapabilities")
    return validation_resolution(
        owner_type="composition_template",
        owner_id=row.id,
        owner_revision=int(row.version),
        graph={
            "templateKey": row.template_key,
            "templateContentHash": row.content_hash,
            "verifiedCapabilities": (
                list(verified) if isinstance(verified, list) else []
            ),
        },
        issues=issues,
    )


__all__ = ["resolve_template_dependencies"]
