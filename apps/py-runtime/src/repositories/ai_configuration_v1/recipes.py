from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from domain.models.ai_configuration_v1 import AccountAIRecipe
from repositories.ai_configuration_v1._support import (
    acquire_sqlite_write_lock,
    limited,
    log_repository_errors,
)

_RECIPE_VALIDATION_STATUSES = frozenset({"incomplete", "valid", "invalid"})


class AccountAIRecipeRepository:
    """在每条查询中强制账号范围并持久化 Recipe 版本。"""

    @log_repository_errors("列出账号 AI Recipe 版本")
    def list(
        self,
        session: Session,
        account_id: str,
        *,
        status: str | None = None,
        validation_status: str | None = None,
        limit: int | None = None,
    ) -> tuple[AccountAIRecipe, ...]:
        statement = select(AccountAIRecipe).where(
            AccountAIRecipe.account_id == account_id
        )
        if status is not None:
            statement = statement.where(AccountAIRecipe.status == status)
        if validation_status is not None:
            statement = statement.where(
                AccountAIRecipe.validation_status == validation_status
            )
        statement = statement.order_by(AccountAIRecipe.version.desc())
        return tuple(session.scalars(limited(statement, limit)).all())

    def list_versions(
        self,
        session: Session,
        account_id: str,
        *,
        limit: int | None = None,
    ) -> tuple[AccountAIRecipe, ...]:
        return self.list(session, account_id, limit=limit)

    @log_repository_errors("读取账号 AI Recipe 版本")
    def get(
        self,
        session: Session,
        account_id: str,
        *,
        version: int,
    ) -> AccountAIRecipe | None:
        return session.scalars(
            select(AccountAIRecipe).where(
                AccountAIRecipe.account_id == account_id,
                AccountAIRecipe.version == version,
            )
        ).one_or_none()

    @log_repository_errors("按标识读取账号 AI Recipe")
    def get_by_id(
        self,
        session: Session,
        account_id: str,
        recipe_id: str,
    ) -> AccountAIRecipe | None:
        return session.scalars(
            select(AccountAIRecipe).where(
                AccountAIRecipe.account_id == account_id,
                AccountAIRecipe.id == recipe_id,
            )
        ).one_or_none()

    @log_repository_errors("读取活动账号 AI Recipe")
    def get_active(
        self,
        session: Session,
        account_id: str,
    ) -> AccountAIRecipe | None:
        return session.scalars(
            select(AccountAIRecipe).where(
                AccountAIRecipe.account_id == account_id,
                AccountAIRecipe.status == "active",
            )
        ).one_or_none()

    @log_repository_errors("计算下一账号 AI Recipe 版本")
    def next_version(
        self,
        session: Session,
        account_id: str,
    ) -> int:
        maximum = session.scalar(
            select(func.max(AccountAIRecipe.version)).where(
                AccountAIRecipe.account_id == account_id
            )
        )
        return int(maximum or 0) + 1

    @log_repository_errors("新增账号 AI Recipe 版本")
    def add(
        self,
        session: Session,
        account_id: str,
        recipe: AccountAIRecipe,
    ) -> AccountAIRecipe:
        if recipe.account_id != account_id:
            raise ValueError("AI Recipe 与调用账号范围不一致")
        if recipe.validation_status not in _RECIPE_VALIDATION_STATUSES:
            raise ValueError("AI Recipe 持久化验证状态无效")
        session.add(recipe)
        session.flush([recipe])
        return recipe

    @log_repository_errors("更新账号 AI Recipe 验证结果")
    def update_validation(
        self,
        session: Session,
        account_id: str,
        *,
        version: int,
        validation_status: str,
        validation_issues_json: str,
        dependency_snapshot_id: str,
        expected_revision: int | None = None,
    ) -> AccountAIRecipe | None:
        if validation_status not in _RECIPE_VALIDATION_STATUSES:
            raise ValueError("AI Recipe 持久化验证状态无效")
        predicates = [
            AccountAIRecipe.account_id == account_id,
            AccountAIRecipe.version == version,
        ]
        if expected_revision is not None:
            predicates.append(AccountAIRecipe.revision == expected_revision)
        statement = (
            update(AccountAIRecipe)
            .where(*predicates)
            .values(
                validation_status=validation_status,
                validation_issues_json=validation_issues_json,
                dependency_snapshot_id=dependency_snapshot_id,
                revision=AccountAIRecipe.revision + 1,
            )
            .returning(AccountAIRecipe)
            .execution_options(
                synchronize_session=False,
                populate_existing=True,
            )
        )
        return session.scalars(statement).one_or_none()

    @log_repository_errors("激活账号 AI Recipe 版本")
    def activate(
        self,
        session: Session,
        account_id: str,
        *,
        version: int,
        expected_revision: int,
        activated_at: str,
    ) -> AccountAIRecipe | None:
        acquire_sqlite_write_lock(session, "account_ai_recipes")
        target = self.get(session, account_id, version=version)
        if (
            target is None
            or target.status == "archived"
            or target.validation_status != "valid"
            or target.revision != expected_revision
        ):
            return None
        if target.status == "active":
            return target
        session.execute(
            update(AccountAIRecipe)
            .where(
                AccountAIRecipe.account_id == account_id,
                AccountAIRecipe.status == "active",
                AccountAIRecipe.id != target.id,
            )
            .values(
                status="archived",
                revision=AccountAIRecipe.revision + 1,
            )
        )
        target.status = "active"
        target.activated_at = activated_at
        target.revision += 1
        session.flush([target])
        return target

    @log_repository_errors("归档账号 AI Recipe 版本")
    def archive(
        self,
        session: Session,
        account_id: str,
        *,
        version: int,
        expected_revision: int,
    ) -> AccountAIRecipe | None:
        acquire_sqlite_write_lock(session, "account_ai_recipes")
        target = self.get(session, account_id, version=version)
        if target is None or target.revision != expected_revision:
            return None
        if target.status != "archived":
            target.status = "archived"
            target.revision += 1
            session.flush([target])
        return target

    @log_repository_errors("失效过期账号 AI Recipe")
    def invalidate_outdated(
        self,
        session: Session,
        *,
        ai_config_revision: int,
        validation_issues_json: str,
    ) -> int:
        result = session.execute(
            update(AccountAIRecipe)
            .where(
                AccountAIRecipe.source_ai_config_revision
                < ai_config_revision,
                AccountAIRecipe.validation_status == "valid",
            )
            .values(
                validation_status="incomplete",
                validation_issues_json=validation_issues_json,
                revision=AccountAIRecipe.revision + 1,
            )
        )
        return int(result.rowcount or 0)

    @log_repository_errors("统计合成模板 Recipe 引用")
    def count_template_references(
        self,
        session: Session,
        template_profile_id: str,
    ) -> int:
        count = session.scalar(
            select(func.count(AccountAIRecipe.id)).where(
                AccountAIRecipe.composition_template_ref
                == template_profile_id
            )
        )
        return int(count or 0)
