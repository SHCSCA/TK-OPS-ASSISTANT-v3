from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request, status

from api.dependencies.account_scope import get_account_scope
from api.dependencies.license_guard import require_active_license
from api.dependencies.pagination import PaginationParams, get_pagination
from api.dependencies.request_context import (
    RequestContext,
    get_request_context,
)
from api.dependencies.resource_id import StablePathId
from api.dependencies.revision import ExpectedRevision, get_expected_revision
from errors import DomainError, ErrorCode, FieldError
from schemas.v1.envelope import ok_response
from schemas.v1.knowledge import (
    KnowledgeIndexInput,
    KnowledgeKind,
    KnowledgeRulesPatchInput,
    KnowledgeSnapshotInput,
    KnowledgeSourceInput,
    KnowledgeSourceStatus,
)
from services.accounts.results import AccountServiceResponse
from services.accounts.scope import AccountScope
from services.accounts.unit_of_work import MutationExecution
from services.knowledge.service import AccountKnowledgeService
from services.knowledge.task_submission import (
    KnowledgeIndexSubmissionService,
)

router = APIRouter(
    prefix="/api/v1/accounts/{account_id}/knowledge",
    tags=["v1-account-knowledge"],
    dependencies=[Depends(require_active_license)],
)

@router.get("")
def get_account_knowledge(
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _knowledge(request).get(scope.account_id)
    return ok_response(result.model_dump(mode="json"))


@router.patch("")
def patch_account_knowledge_rules(
    payload: KnowledgeRulesPatchInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _knowledge(request).patch_rules(
        scope.account_id,
        payload,
        expected_revision=revision.value,
    )
    return ok_response(result.data, meta=result.meta)


@router.get("/sources")
def list_account_knowledge_sources(
    request: Request,
    source_kind: Annotated[
        KnowledgeKind | None,
        Query(alias="kind"),
    ] = None,
    source_status: Annotated[
        KnowledgeSourceStatus | None,
        Query(alias="status"),
    ] = None,
    pagination: PaginationParams = Depends(get_pagination),
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    filters: dict[str, object] = {
        "kind": source_kind,
        "status": source_status,
    }
    cursor = pagination.decode_cursor(
        scope=scope.account_id,
        resource_kind="knowledge.sources",
        filters=filters,
    )
    result, next_position = _knowledge(request).list_sources(
        scope.account_id,
        limit=pagination.limit,
        cursor=cursor,
        kind=source_kind,
        status=source_status,
    )
    next_cursor = pagination.encode_cursor(
        next_position,
        scope=scope.account_id,
        resource_kind="knowledge.sources",
        filters=filters,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={"nextCursor": next_cursor},
    )


@router.post("/sources", status_code=status.HTTP_201_CREATED)
def create_account_knowledge_source(
    payload: KnowledgeSourceInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    execution = _knowledge(request).create_source(
        scope.account_id,
        payload,
        idempotency_key=_require_idempotency_key(context),
    )
    return _mutation_response(execution)


@router.delete("/sources/{source_id}")
def remove_account_knowledge_source(
    request: Request,
    source_id: StablePathId,
    scope: AccountScope = Depends(get_account_scope),
    revision: ExpectedRevision = Depends(get_expected_revision),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    execution = _knowledge(request).remove_source(
        scope.account_id,
        source_id,
        expected_revision=revision.value,
        idempotency_key=_require_idempotency_key(context),
    )
    return _mutation_response(execution)


@router.post("/index-jobs", status_code=status.HTTP_202_ACCEPTED)
async def submit_account_knowledge_index_job(
    payload: KnowledgeIndexInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = await _knowledge_index(request).submit(
        scope.account_id,
        payload,
        idempotency_key=_require_idempotency_key(context),
        request_id=context.request_id,
        operation_id=context.operation_id,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={
            "invalidations": [
                f"account:{scope.account_id}:tasks",
                f"account:{scope.account_id}:knowledge",
            ]
        },
    )


@router.get("/snapshots")
def list_account_knowledge_snapshots(
    request: Request,
    pagination: PaginationParams = Depends(get_pagination),
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    filters: dict[str, object] = {}
    cursor = pagination.decode_cursor(
        scope=scope.account_id,
        resource_kind="knowledge.snapshots",
        filters=filters,
    )
    result, next_position = _knowledge(request).list_snapshots(
        scope.account_id,
        limit=pagination.limit,
        cursor=cursor,
    )
    next_cursor = pagination.encode_cursor(
        next_position,
        scope=scope.account_id,
        resource_kind="knowledge.snapshots",
        filters=filters,
    )
    return ok_response(
        result.model_dump(mode="json"),
        meta={"nextCursor": next_cursor},
    )


@router.post("/snapshots", status_code=status.HTTP_201_CREATED)
def create_account_knowledge_snapshot(
    payload: KnowledgeSnapshotInput,
    request: Request,
    scope: AccountScope = Depends(get_account_scope),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    execution = _knowledge(request).create_snapshot(
        scope.account_id,
        payload,
        idempotency_key=_require_idempotency_key(context),
    )
    return _mutation_response(execution)


@router.get("/snapshots/{snapshot_id}")
def get_account_knowledge_snapshot(
    request: Request,
    snapshot_id: StablePathId,
    scope: AccountScope = Depends(get_account_scope),
    _: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    result = _knowledge(request).get_snapshot(
        scope.account_id,
        snapshot_id,
    )
    return ok_response(result.model_dump(mode="json"))


def _knowledge(request: Request) -> AccountKnowledgeService:
    return cast(
        AccountKnowledgeService,
        _resolve_service(
            request,
            bundle_name="knowledge",
            direct_name="account_knowledge_service",
        ),
    )


def _knowledge_index(
    request: Request,
) -> KnowledgeIndexSubmissionService:
    return cast(
        KnowledgeIndexSubmissionService,
        _resolve_service(
            request,
            bundle_name="knowledge_index",
            direct_name="knowledge_index_submission_service",
        ),
    )


def _resolve_service(
    request: Request,
    *,
    bundle_name: str,
    direct_name: str,
) -> object:
    direct = getattr(request.app.state, direct_name, None)
    if direct is not None:
        return direct
    state_bundle = getattr(request.app.state, "account_v1_service", None)
    service = getattr(state_bundle, bundle_name, None)
    if service is not None:
        return service
    container = getattr(request.app.state, "runtime_container", None)
    services = getattr(container, "services", None)
    for bundle_key in ("account_v1", "account_runtime"):
        bundle = getattr(services, bundle_key, None)
        service = getattr(bundle, bundle_name, None)
        if service is not None:
            return service
    service = getattr(services, bundle_name, None)
    if service is not None:
        return service
    raise DomainError(
        ErrorCode.RUNTIME_NOT_READY,
        "账号知识服务尚未就绪",
        status_code=503,
        loggable=True,
        log_context={
            "operation": "account.knowledge.route.resolve_service",
            "service": bundle_name,
        },
    )


def _require_idempotency_key(context: RequestContext) -> str:
    if context.idempotency_key is not None:
        return context.idempotency_key
    raise DomainError(
        ErrorCode.REQUEST_VALIDATION_FAILED,
        "写操作必须提供 Idempotency-Key",
        status_code=422,
        field_errors=[
            FieldError(
                field="Idempotency-Key",
                code="required",
                message="必须提供幂等键",
            )
        ],
    )


def _mutation_response(
    execution: MutationExecution,
) -> dict[str, object]:
    result = AccountServiceResponse.from_mutation(execution)
    return ok_response(result.data, meta=result.meta)
