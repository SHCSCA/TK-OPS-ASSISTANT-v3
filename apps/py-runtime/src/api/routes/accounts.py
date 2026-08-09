from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Request

from api.routes.legacy.access import (
    legacy_write_unsupported,
    record_legacy_api_use,
)
from schemas.envelope import ok_response
from services.account_service import AccountService

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

_ACCOUNT_GROUP_REPLACEMENT = "无替代接口；账号分组已退出当前产品范围"


def _svc(request: Request) -> AccountService:
    return request.app.state.account_service  # type: ignore[no-any-return]


def _reject_legacy_write(
    request: Request,
    *,
    replacement: str,
) -> NoReturn:
    record_legacy_api_use(request, replacement=replacement)
    legacy_write_unsupported(replacement=replacement)


# 静态子路径必须位于 /{account_id} 之前，避免被动态路由遮蔽

@router.get("/groups")
def list_account_groups(request: Request) -> dict[str, object]:
    groups = _svc(request).list_groups()
    return ok_response([g.model_dump(mode="json") for g in groups])


@router.post("/groups")
def create_account_group(request: Request) -> None:
    _reject_legacy_write(
        request,
        replacement=_ACCOUNT_GROUP_REPLACEMENT,
    )


@router.patch("/groups/{group_id}")
def update_account_group(group_id: str, request: Request) -> None:
    del group_id
    _reject_legacy_write(
        request,
        replacement=_ACCOUNT_GROUP_REPLACEMENT,
    )


@router.delete("/groups/{group_id}")
def delete_account_group(group_id: str, request: Request) -> None:
    del group_id
    _reject_legacy_write(
        request,
        replacement=_ACCOUNT_GROUP_REPLACEMENT,
    )


@router.get("/groups/{group_id}/members")
def list_group_members(group_id: str, request: Request) -> dict[str, object]:
    members = _svc(request).list_group_members(group_id)
    return ok_response([m.model_dump(mode="json") for m in members])


@router.post("/groups/{group_id}/members")
def add_group_member(group_id: str, request: Request) -> None:
    del group_id
    _reject_legacy_write(
        request,
        replacement=_ACCOUNT_GROUP_REPLACEMENT,
    )


@router.delete("/groups/{group_id}/members/{account_id}")
def remove_group_member(
    group_id: str,
    account_id: str,
    request: Request,
) -> None:
    del group_id, account_id
    _reject_legacy_write(
        request,
        replacement=_ACCOUNT_GROUP_REPLACEMENT,
    )


@router.get("")
def list_accounts(
    request: Request,
    status: str | None = None,
    platform: str | None = None,
    group_id: str | None = None,
    q: str | None = None,
) -> dict[str, object]:
    accounts = _svc(request).list_accounts(status=status, platform=platform, group_id=group_id, q=q)
    return ok_response([a.model_dump(mode="json") for a in accounts])


@router.post("")
def create_account(request: Request) -> None:
    _reject_legacy_write(
        request,
        replacement="POST /api/v1/accounts",
    )


@router.get("/{account_id}")
def get_account(account_id: str, request: Request) -> dict[str, object]:
    account = _svc(request).get_account(account_id)
    return ok_response(account.model_dump(mode="json"))


@router.put("/{account_id}/binding")
def upsert_account_binding(
    account_id: str,
    request: Request,
) -> None:
    del account_id
    _reject_legacy_write(
        request,
        replacement=(
            "PUT /api/v1/accounts/{account_id}/connection/binding"
        ),
    )


@router.patch("/{account_id}")
def update_account(
    account_id: str,
    request: Request,
) -> None:
    del account_id
    _reject_legacy_write(
        request,
        replacement="PATCH /api/v1/accounts/{account_id}",
    )


@router.delete("/{account_id}")
def delete_account(account_id: str, request: Request) -> None:
    del account_id
    _reject_legacy_write(
        request,
        replacement="POST /api/v1/accounts/{account_id}/archive",
    )


@router.post("/{account_id}/refresh-stats")
def refresh_account_stats(account_id: str, request: Request) -> None:
    del account_id
    _reject_legacy_write(
        request,
        replacement=(
            "POST /api/v1/accounts/{account_id}/health-checks"
        ),
    )
