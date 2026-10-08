from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from domain.models.account_asset import AccountAsset, KnowledgeSourceAsset
from errors import DomainError, ErrorCode
from schemas.v1.knowledge import KnowledgeSourceInput
from services.accounts.json_codec import dump_json
from services.accounts.unit_of_work import AccountTransaction
from services.knowledge.content_store import KnowledgeContentStore
from services.knowledge.ports import ControlledFileGrant, ControlledFileResolver
from services.knowledge.source_validation import (
    normalize_public_https_url,
    require_controlled_file_ref,
)


@dataclass(frozen=True, slots=True)
class PreparedKnowledgeSource:
    source_ref: str
    source_url: str | None
    metadata: dict[str, object]
    controlled_file: ControlledFileGrant | None = None


class KnowledgeSourceMaterialPreparer:
    def __init__(
        self,
        *,
        content_store: KnowledgeContentStore,
        controlled_files: ControlledFileResolver,
        max_controlled_file_bytes: Callable[[], int],
    ) -> None:
        self._content_store = content_store
        self._controlled_files = controlled_files
        self._max_controlled_file_bytes = max_controlled_file_bytes

    def prepare(
        self,
        account_id: str,
        source_id: str,
        payload: KnowledgeSourceInput,
        *,
        stored_refs: list[str],
    ) -> PreparedKnowledgeSource:
        if payload.sourceMode == "file":
            reference = require_controlled_file_ref(
                payload.controlledFileRef or ""
            )
            grant = self._controlled_files.describe(
                account_id,
                reference,
                max_bytes=self._max_controlled_file_bytes(),
            )
            if payload.kind != grant.kind:
                raise DomainError(
                    ErrorCode.KNOWLEDGE_SOURCE_INVALID,
                    "知识来源类型与受控文件类型不一致",
                    status_code=422,
                )
            return PreparedKnowledgeSource(
                source_ref=reference,
                source_url=None,
                metadata={
                    "sourceMode": "file",
                    "rootRef": grant.root_ref,
                    "rootRevision": grant.root_revision,
                    "fileGrantRevision": grant.file_revision,
                    "fileFingerprint": grant.fingerprint,
                },
                controlled_file=grant,
            )
        if payload.sourceMode == "url":
            url = normalize_public_https_url(payload.url or "")
            digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
            return PreparedKnowledgeSource(
                source_ref=f"url-ref:{digest}",
                source_url=url,
                metadata={"sourceMode": "url"},
            )
        stored = self._content_store.store_text(
            account_id,
            source_id,
            payload.text or "",
        )
        stored_refs.append(stored.reference)
        return PreparedKnowledgeSource(
            source_ref=stored.reference,
            source_url=None,
            metadata={
                "sourceMode": "text",
                "byteSize": stored.byte_size,
                "expectedContentHash": stored.content_hash,
            },
        )

    def persist_controlled_asset(
        self,
        transaction: AccountTransaction,
        *,
        account_id: str,
        source_id: str,
        prepared: PreparedKnowledgeSource,
        now: str,
    ) -> AccountAsset | None:
        grant = prepared.controlled_file
        if grant is None:
            return None
        asset = transaction.knowledge_assets.add_asset(
            account_id,
            transaction.session,
            AccountAsset(
                id=f"asset_{uuid4().hex}",
                account_id=account_id,
                kind=grant.kind,
                source_kind="controlled_file",
                controlled_file_ref=grant.file_ref,
                root_ref=grant.root_ref,
                display_name=grant.display_name,
                media_type=grant.media_type,
                byte_size=grant.byte_size,
                content_hash=None,
                status="pending",
                authorization_basis=dump_json(
                    {
                        "fileGrantRevision": grant.file_revision,
                        "rootRevision": grant.root_revision,
                        "fingerprint": grant.fingerprint,
                    }
                ),
                error_code=None,
                error_log_id=None,
                revision=1,
                created_at=now,
                updated_at=now,
            ),
        )
        transaction.knowledge_assets.link_source(
            account_id,
            transaction.session,
            KnowledgeSourceAsset(
                account_id=account_id,
                knowledge_source_id=source_id,
                account_asset_id=asset.id,
                created_at=now,
            ),
        )
        return asset

    def cleanup(
        self,
        account_id: str,
        references: list[str],
    ) -> None:
        for reference in references:
            self._content_store.remove(account_id, reference)
