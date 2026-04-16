from __future__ import annotations

from fastapi import APIRouter, Request

from schemas.accounts import (
    AccountCreateInput,
    AccountGroupCreateInput,
    AccountGroupMemberCreateInput,
    AccountGroupUpdateInput,
    AccountUpdateInput,
)
from schemas.envelope import ok_response
from services.account_service import AccountService

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _svc(request: Request) -> AccountService:
    return request.app.state.account_service  # type: ignore[no-any-return]


# NOTE: static sub-paths must be declared BEFORE /{account_id} to avoid shadowing

@router.get("/groups")
def list_account_groups(request: Request) -> dict[str, object]:
    groups = _svc(request).list_groups()
    return ok_response([g.model_dump(mode="json") for g in groups])


@router.post("/groups")
def create_account_group(payload: AccountGroupCreateInput, request: Request) -> dict[str, object]:
    group = _svc(request).create_group(payload)
    return ok_response(group.model_dump(mode="json"))


@router.patch("/groups/{group_id}")
def update_account_group(group_id: str, payload: AccountGroupUpdateInput, request: Request) -> dict[str, object]:
    group = _svc(request).update_group(group_id, payload)
    return ok_response(group.model_dump(mode="json"))


@router.delete("/groups/{group_id}")
def delete_account_group(group_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).delete_group(group_id)
    return ok_response(result)


@router.get("/groups/{group_id}/members")
def list_group_members(group_id: str, request: Request) -> dict[str, object]:
    members = _svc(request).list_group_members(group_id)
    return ok_response([m.model_dump(mode="json") for m in members])


@router.post("/groups/{group_id}/members")
def add_group_member(group_id: str, payload: AccountGroupMemberCreateInput, request: Request) -> dict[str, object]:
    result = _svc(request).add_group_member(group_id, payload)
    return ok_response(result)


@router.delete("/groups/{group_id}/members/{account_id}")
def remove_group_member(group_id: str, account_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).remove_group_member(group_id=group_id, account_id=account_id)
    return ok_response(result)


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
def create_account(payload: AccountCreateInput, request: Request) -> dict[str, object]:
    account = _svc(request).create_account(payload)
    return ok_response(account.model_dump(mode="json"))


@router.get("/{account_id}")
def get_account(account_id: str, request: Request) -> dict[str, object]:
    account = _svc(request).get_account(account_id)
    return ok_response(account.model_dump(mode="json"))


@router.patch("/{account_id}")
def update_account(account_id: str, payload: AccountUpdateInput, request: Request) -> dict[str, object]:
    account = _svc(request).update_account(account_id, payload)
    return ok_response(account.model_dump(mode="json"))


@router.delete("/{account_id}")
def delete_account(account_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).delete_account(account_id)
    return ok_response(result)


@router.post("/{account_id}/refresh-stats")
def refresh_account_stats(account_id: str, request: Request) -> dict[str, object]:
    result = _svc(request).refresh_stats(account_id)
    return ok_response(result.model_dump(mode="json"))
