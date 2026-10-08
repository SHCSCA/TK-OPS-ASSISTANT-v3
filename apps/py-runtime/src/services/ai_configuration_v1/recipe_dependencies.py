from __future__ import annotations

from collections.abc import Mapping

from domain.models.ai_configuration_v1 import AccountAIRecipe
from services.ai_execution_v1.dependency_graph import DependencyResolution

from .dependency_snapshots import validation_resolution
from .recipe_validation import validate_recipe
from .unit_of_work import AIConfigurationTransaction


def resolve_recipe_dependencies(
    transaction: AIConfigurationTransaction,
    row: AccountAIRecipe,
    *,
    validation: Mapping[str, object] | None = None,
) -> DependencyResolution:
    result = dict(validation or validate_recipe(transaction, row))
    raw_issues = result.get("validationIssues")
    issues = (
        tuple(item for item in raw_issues if isinstance(item, Mapping))
        if isinstance(raw_issues, list)
        else ()
    )
    resolved = result.get("resolvedRouteSummary")
    return validation_resolution(
        owner_type="recipe",
        owner_id=row.id,
        owner_revision=int(row.version),
        graph={
            "accountId": row.account_id,
            "recipeContentHash": row.content_hash,
            "sourceAiConfigRevision": int(row.source_ai_config_revision),
            "resolvedRouteSummary": (
                dict(resolved) if isinstance(resolved, Mapping) else {}
            ),
            "compositionTemplateRef": row.composition_template_ref,
        },
        issues=issues,
    )


__all__ = ["resolve_recipe_dependencies"]
