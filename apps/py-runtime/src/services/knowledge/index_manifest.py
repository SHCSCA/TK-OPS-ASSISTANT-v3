from __future__ import annotations

from collections.abc import Mapping, Sequence

from domain.models.account_asset import AccountAsset
from domain.models.knowledge import KnowledgeSource
from errors import DomainError, ErrorCode
from services.accounts.json_codec import load_json_object
from services.knowledge.index_types import (
    KnowledgeIndexPlan,
    KnowledgeIndexSourceManifest,
)


def build_index_plan(
    account_id: str,
    sources: Sequence[KnowledgeSource],
    assets: Mapping[str, AccountAsset],
) -> KnowledgeIndexPlan:
    manifests = tuple(
        _source_manifest(source, assets.get(source.id))
        for source in sources
    )
    return KnowledgeIndexPlan(
        account_id=account_id,
        source_ids=tuple(item.source_id for item in manifests),
        source_manifests=manifests,
    )


def _source_manifest(
    source: KnowledgeSource,
    asset: AccountAsset | None,
) -> KnowledgeIndexSourceManifest:
    if source.source_mode != "file":
        return KnowledgeIndexSourceManifest(
            source_id=source.id,
            source_revision=int(source.revision),
            source_mode=source.source_mode,
        )
    if asset is None or asset.controlled_file_ref != source.source_ref:
        raise _invalid_manifest("受控文件来源缺少账号资产关联")
    basis = load_json_object(
        asset.authorization_basis,
        resource_label="受控文件授权证据",
    )
    grant_revision = basis.get("fileGrantRevision")
    root_revision = basis.get("rootRevision")
    fingerprint = basis.get("fingerprint")
    if (
        isinstance(grant_revision, bool)
        or not isinstance(grant_revision, int)
        or grant_revision < 1
        or isinstance(root_revision, bool)
        or not isinstance(root_revision, int)
        or root_revision < 1
        or not isinstance(fingerprint, str)
        or len(fingerprint) != 64
    ):
        raise _invalid_manifest("受控文件授权证据结构无效")
    return KnowledgeIndexSourceManifest(
        source_id=source.id,
        source_revision=int(source.revision),
        source_mode="file",
        file_ref=asset.controlled_file_ref,
        root_ref=asset.root_ref,
        root_revision=root_revision,
        file_revision=grant_revision,
        fingerprint=fingerprint,
    )


def _invalid_manifest(message: str) -> DomainError:
    return DomainError(
        ErrorCode.KNOWLEDGE_SOURCE_INVALID,
        message,
        status_code=422,
        loggable=True,
    )
