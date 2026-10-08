from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass

from domain.models.account_configuration import PositioningProfile
from domain.models.ai_execution import AIExecution
from domain.models.ai_execution_snapshot import (
    AIDependencySnapshot,
    AIExecutionCandidate,
    AIExecutionSnapshot,
)
from errors import DomainError, ErrorCode
from services.ai_configuration_v1.json_codec import content_hash, load_object

from .content_store import AIExecutionContentStore
from .knowledge_context import KnowledgeContextResolver
from .policies import ExecutionPolicy, execution_policy_from_snapshot
from .prompt_renderer import RenderedPrompt, render_prompt
from .unit_of_work import AIExecutionTransaction


@dataclass(frozen=True, slots=True)
class FrozenExecutionMaterial:
    execution: AIExecution
    snapshot: AIExecutionSnapshot
    candidates: tuple[AIExecutionCandidate, ...]
    input_value: dict[str, object]
    rendered_prompt: RenderedPrompt
    policy: ExecutionPolicy


class AIExecutionMaterialLoader:
    """在每次 Provider 调用前重读正文并验证全部冻结哈希。"""

    def __init__(
        self,
        *,
        content_store: AIExecutionContentStore,
        knowledge_context: KnowledgeContextResolver,
    ) -> None:
        self._content_store = content_store
        self._knowledge_context = knowledge_context

    def load(
        self,
        transaction: AIExecutionTransaction,
        *,
        account_id: str,
        execution_id: str,
    ) -> FrozenExecutionMaterial:
        execution = transaction.executions.executions.get_scoped(
            transaction.session,
            account_id,
            execution_id,
        )
        if execution is None:
            raise DomainError(
                ErrorCode.AI_EXECUTION_NOT_FOUND,
                "AI 执行不存在",
                status_code=404,
            )
        snapshot = transaction.executions.snapshots.get_snapshot(
            transaction.session,
            account_id,
            execution.snapshot_id,
        )
        if snapshot is None:
            raise _invalid_snapshot()
        input_value, input_hash = self._content_store.read_input(
            account_id,
            execution.input_ref,
        )
        if input_hash != execution.input_hash:
            raise _invalid_snapshot()
        knowledge_snapshot = transaction.knowledge.get_snapshot(
            account_id,
            transaction.session,
            snapshot_id=snapshot.knowledge_snapshot_id,
        )
        prompt = transaction.ai.prompts.get_by_id(
            transaction.session,
            snapshot.prompt_profile_id,
        )
        dependency = transaction.session.get(
            AIDependencySnapshot,
            snapshot.dependency_snapshot_id,
        )
        recipe = transaction.ai.recipes.get_by_id(
            transaction.session,
            account_id,
            snapshot.account_recipe_id,
        )
        route = transaction.ai.route_revisions.get_by_id(
            transaction.session,
            snapshot.route_revision_id,
        )
        if (
            snapshot.account_id != account_id
            or snapshot.capability_key != execution.capability_key
            or knowledge_snapshot is None
            or knowledge_snapshot.content_hash != snapshot.knowledge_content_hash
            or int(knowledge_snapshot.snapshot_version)
            != int(snapshot.knowledge_snapshot_version)
            or prompt is None
            or int(prompt.version) != int(snapshot.prompt_version)
            or int(prompt.revision) != int(snapshot.prompt_revision)
            or prompt.content_hash != snapshot.prompt_content_hash
            or recipe is None
            or int(recipe.version) != int(snapshot.recipe_version)
            or int(recipe.revision) != int(snapshot.recipe_revision)
            or recipe.content_hash != snapshot.recipe_content_hash
            or route is None
            or route.capability_route_id != snapshot.capability_route_id
            or route.capability_key != snapshot.capability_key
            or route.content_hash != snapshot.route_content_hash
            or dependency is None
            or dependency.status != "valid"
            or dependency.owner_type != "execution_preflight"
            or dependency.owner_id != execution.id
            or int(dependency.owner_revision) != 1
        ):
            raise _invalid_snapshot()
        dependency_graph = load_object(
            dependency.graph_json,
            label="AI 执行依赖图",
        )
        if content_hash(dependency_graph) != dependency.content_hash:
            raise _invalid_snapshot()
        positioning = _load_positioning(
            transaction,
            account_id=account_id,
            snapshot=snapshot,
        )
        policy = execution_policy_from_snapshot(snapshot.policy_json)
        knowledge = self._knowledge_context.resolve(
            transaction,
            account_id=account_id,
            snapshot=knowledge_snapshot,
            max_input_units=policy.knowledge_max_input_units,
        )
        if knowledge.manifest_hash != snapshot.context_manifest_hash:
            raise _invalid_snapshot()
        rendered = render_prompt(
            prompt,
            input_value=input_value,
            knowledge=knowledge,
            positioning=positioning,
        )
        if (
            rendered.rendered_hash != snapshot.rendered_prompt_hash
            or rendered.input_schema_hash != snapshot.input_schema_hash
            or rendered.output_schema_hash != snapshot.output_schema_hash
        ):
            raise _invalid_snapshot()
        expected_snapshot_hash = content_hash(
            {
                "dependencyHash": dependency.content_hash,
                "inputHash": input_hash,
                "renderedPromptHash": rendered.rendered_hash,
            }
        )
        if expected_snapshot_hash != snapshot.snapshot_hash:
            raise _invalid_snapshot()
        candidates = transaction.executions.snapshots.list_candidates(
            transaction.session,
            account_id,
            snapshot.id,
        )
        if not candidates or not _dependency_graph_matches(
            dependency_graph,
            execution=execution,
            snapshot=snapshot,
            candidates=candidates,
        ):
            raise _invalid_snapshot()
        return FrozenExecutionMaterial(
            execution=execution,
            snapshot=snapshot,
            candidates=candidates,
            input_value=input_value,
            rendered_prompt=rendered,
            policy=policy,
        )


def _load_positioning(
    transaction: AIExecutionTransaction,
    *,
    account_id: str,
    snapshot: AIExecutionSnapshot,
) -> PositioningProfile | None:
    if snapshot.positioning_profile_id is None:
        if snapshot.positioning_content_hash is not None:
            raise _invalid_snapshot()
        return None
    row = transaction.session.get(
        PositioningProfile,
        snapshot.positioning_profile_id,
    )
    if (
        row is None
        or row.account_id != account_id
        or int(row.version) != int(snapshot.positioning_version or 0)
        or _positioning_hash(row) != snapshot.positioning_content_hash
    ):
        raise _invalid_snapshot()
    return row


def _positioning_hash(row: PositioningProfile) -> str:
    try:
        return content_hash(
            {
                "id": row.id,
                "version": int(row.version),
                "audience": json.loads(row.audience_json),
                "contentPillars": json.loads(row.content_pillars_json),
                "voiceStyle": json.loads(row.voice_style_json),
                "prohibitedTerms": json.loads(row.prohibited_terms_json),
                "publishingConstraints": json.loads(
                    row.publishing_constraints_json
                ),
                "summary": row.summary,
            }
        )
    except (TypeError, json.JSONDecodeError) as exc:
        raise _invalid_snapshot() from exc


def _dependency_graph_matches(
    graph: dict[str, object],
    *,
    execution: AIExecution,
    snapshot: AIExecutionSnapshot,
    candidates: Sequence[AIExecutionCandidate],
) -> bool:
    raw_candidates = graph.get("candidates")
    if not isinstance(raw_candidates, list) or len(raw_candidates) != len(
        candidates
    ):
        return False
    if [int(item.ordinal) for item in candidates] != list(range(len(candidates))):
        return False
    for candidate, frozen in zip(candidates, raw_candidates, strict=True):
        if not isinstance(frozen, dict):
            return False
        if content_hash(frozen) != candidate.snapshot_hash:
            return False
    return all(
        (
            graph.get("accountId") == execution.account_id,
            graph.get("accountRevision") == int(snapshot.account_revision),
            graph.get("aiConfigRevision") == int(snapshot.ai_config_revision),
            graph.get("recipeId") == snapshot.account_recipe_id,
            graph.get("recipeContentHash") == snapshot.recipe_content_hash,
            graph.get("routeId") == snapshot.capability_route_id,
            graph.get("routeRevisionId") == snapshot.route_revision_id,
            graph.get("routeContentHash") == snapshot.route_content_hash,
            graph.get("promptProfileId") == snapshot.prompt_profile_id,
            graph.get("promptVersion") == int(snapshot.prompt_version),
            graph.get("promptContentHash") == snapshot.prompt_content_hash,
            graph.get("knowledgeSnapshotId") == snapshot.knowledge_snapshot_id,
            graph.get("knowledgeContentHash") == snapshot.knowledge_content_hash,
            graph.get("contextManifestHash") == snapshot.context_manifest_hash,
            graph.get("policy")
            == load_object(snapshot.policy_json, label="AI 执行策略快照"),
        )
    )


def _invalid_snapshot() -> DomainError:
    return DomainError(
        ErrorCode.AI_DEPENDENCY_INVALID,
        "AI 执行冻结快照完整性校验失败",
        status_code=409,
        loggable=True,
    )


__all__ = ["AIExecutionMaterialLoader", "FrozenExecutionMaterial"]
