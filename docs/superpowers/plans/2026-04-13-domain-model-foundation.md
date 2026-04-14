# Domain Model 基础层落地实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `apps/py-runtime/src/domain/models/` 从空壳落地为真实的 SQLAlchemy ORM 模型层，覆盖当前已有数据表（`projects`、`script_versions`、`storyboard_versions`、`ai_job_records`、`ai_capability_configs`、`license_grant`、`system_config`、`session_context`），并为后续视频拆解、时间线、配音、字幕等模型扩展建立稳定基线。

**Architecture:** 当前后端使用原生 `sqlite3` + 手写 SQL，Repository 层直接操作 `sqlite3.Connection`。本轮引入 SQLAlchemy 2.0 声明式模型，在 `domain/models/` 下定义所有持久化实体，迁移引擎从手写 migration 函数切换到 Alembic。Repository 层改为通过 SQLAlchemy Session 操作模型对象。服务层接口不变，前端零改动。

**Tech Stack:** SQLAlchemy 2.0（Mapped 声明式）、Alembic、Python 3.13+、SQLite

---

## 边界

- 不新增业务页面或前端改动
- 不新增 API 端点
- 不改变现有 API 返回结构
- 不删除现有手写 migration 函数（保留为参考，Alembic 初始 migration 产生等效 schema）
- 现有测试必须全部通过

## 文件结构

### 新建文件

| 文件 | 职责 |
|------|------|
| `apps/py-runtime/src/domain/__init__.py` | 包初始化 |
| `apps/py-runtime/src/domain/models/__init__.py` | 导出所有模型和 Base |
| `apps/py-runtime/src/domain/models/base.py` | SQLAlchemy DeclarativeBase、通用 mixin（时间戳、ID 策略） |
| `apps/py-runtime/src/domain/models/project.py` | `Project` 模型 |
| `apps/py-runtime/src/domain/models/script.py` | `ScriptVersion` 模型 |
| `apps/py-runtime/src/domain/models/storyboard.py` | `StoryboardVersion` 模型 |
| `apps/py-runtime/src/domain/models/ai_job.py` | `AIJobRecord` 模型 |
| `apps/py-runtime/src/domain/models/ai_capability.py` | `AICapabilityConfig`、`AIProviderSetting` 模型 |
| `apps/py-runtime/src/domain/models/license.py` | `LicenseGrant` 模型 |
| `apps/py-runtime/src/domain/models/system_config.py` | `SystemConfig`、`SessionContext` 模型 |
| `apps/py-runtime/src/persistence/engine.py` | SQLAlchemy `create_engine` + `sessionmaker` 工厂 |
| `apps/py-runtime/alembic.ini` | Alembic 配置 |
| `apps/py-runtime/alembic/env.py` | Alembic 迁移环境 |
| `apps/py-runtime/alembic/versions/0001_initial_schema.py` | 初始 migration（等效现有 schema_version=3） |
| `tests/runtime/test_domain_models.py` | 模型层单元测试 |
| `tests/runtime/test_repository_orm.py` | Repository ORM 集成测试 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `apps/py-runtime/src/persistence/sqlite.py` | 新增 `get_engine()` / `get_session()` 工厂，保留旧 `connect_sqlite` 做渐进迁移 |
| `apps/py-runtime/src/app/factory.py` | 初始化 SQLAlchemy engine，注入 Session 工厂到各 Repository |
| `apps/py-runtime/src/repositories/dashboard_repository.py` | 从原生 SQL 迁移到 SQLAlchemy Session 操作 |
| `apps/py-runtime/src/repositories/script_repository.py` | 同上 |
| `apps/py-runtime/src/repositories/storyboard_repository.py` | 同上 |
| `apps/py-runtime/src/repositories/ai_capability_repository.py` | 同上 |
| `apps/py-runtime/src/repositories/ai_job_repository.py` | 同上 |
| `apps/py-runtime/src/repositories/license_repository.py` | 同上 |
| `apps/py-runtime/src/repositories/system_config_repository.py` | 同上 |
| `apps/py-runtime/pyproject.toml` | 确认 `sqlalchemy` 和 `alembic` 已在 dependencies（已存在） |

---

## 任务

### Task 1: SQLAlchemy Base 与通用 Mixin

**Files:**
- Create: `apps/py-runtime/src/domain/__init__.py`
- Create: `apps/py-runtime/src/domain/models/__init__.py`
- Create: `apps/py-runtime/src/domain/models/base.py`
- Test: `tests/runtime/test_domain_models.py`

- [ ] **Step 1: 编写 Base 和 Mixin 的失败测试**

```python
# tests/runtime/test_domain_models.py
from __future__ import annotations

from domain.models.base import Base, generate_uuid


def test_base_registry_exists():
    assert hasattr(Base, "metadata")
    assert Base.metadata is not None


def test_generate_uuid_returns_32_char_hex():
    uid = generate_uuid()
    assert isinstance(uid, str)
    assert len(uid) == 32
    assert uid.isalnum()
```

- [ ] **Step 2: 运行测试确认失败**

运行: `venv\\Scripts\\python.exe -m pytest tests/runtime/test_domain_models.py -v`
预期: FAIL — `ModuleNotFoundError: No module named 'domain.models.base'`

- [ ] **Step 3: 实现 Base 和工具函数**

```python
# apps/py-runtime/src/domain/__init__.py
from __future__ import annotations

# apps/py-runtime/src/domain/models/__init__.py
from __future__ import annotations

from domain.models.base import Base, generate_uuid

__all__ = ["Base", "generate_uuid"]

# apps/py-runtime/src/domain/models/base.py
from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 Domain Model 的声明式基类。"""
    pass


def generate_uuid() -> str:
    """生成 32 位十六进制 UUID，用作主键默认值。"""
    return uuid4().hex
```

- [ ] **Step 4: 运行测试确认通过**

运行: `venv\\Scripts\\python.exe -m pytest tests/runtime/test_domain_models.py -v`
预期: PASS

- [ ] **Step 5: 提交**

```bash
git add apps/py-runtime/src/domain/ tests/runtime/test_domain_models.py
git commit -m "feat: 添加 SQLAlchemy Base 声明式基类和 UUID 工具"
```

---

### Task 2: Project 模型

**Files:**
- Create: `apps/py-runtime/src/domain/models/project.py`
- Modify: `apps/py-runtime/src/domain/models/__init__.py`
- Test: `tests/runtime/test_domain_models.py`

- [ ] **Step 1: 编写 Project 模型的失败测试**

```python
# tests/runtime/test_domain_models.py （追加）
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from domain.models.base import Base
from domain.models.project import Project


def test_project_table_name():
    assert Project.__tablename__ == "projects"


def test_project_columns_match_existing_schema():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("projects")}
    expected = {
        "id", "name", "description", "status",
        "current_script_version", "current_storyboard_version",
        "created_at", "updated_at", "last_accessed_at",
    }
    assert expected == columns


def test_project_crud_roundtrip():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        project = Project(
            id="abc123",
            name="测试项目",
            description="描述",
            status="active",
            current_script_version=0,
            current_storyboard_version=0,
            created_at="2026-04-13T00:00:00Z",
            updated_at="2026-04-13T00:00:00Z",
            last_accessed_at="2026-04-13T00:00:00Z",
        )
        session.add(project)
        session.commit()

        loaded = session.get(Project, "abc123")
        assert loaded is not None
        assert loaded.name == "测试项目"
        assert loaded.status == "active"
```

- [ ] **Step 2: 运行测试确认失败**

运行: `venv\\Scripts\\python.exe -m pytest tests/runtime/test_domain_models.py::test_project_table_name -v`
预期: FAIL — `ModuleNotFoundError: No module named 'domain.models.project'`

- [ ] **Step 3: 实现 Project 模型**

```python
# apps/py-runtime/src/domain/models/project.py
from __future__ import annotations

from sqlalchemy import String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class Project(Base):
    """项目根对象，聚合创作上下文。"""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    current_script_version: Mapped[int] = mapped_column(Integer, nullable=False)
    current_storyboard_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
    last_accessed_at: Mapped[str] = mapped_column(Text, nullable=False)
```

更新 `__init__.py`：
```python
# apps/py-runtime/src/domain/models/__init__.py
from __future__ import annotations

from domain.models.base import Base, generate_uuid
from domain.models.project import Project

__all__ = ["Base", "generate_uuid", "Project"]
```

- [ ] **Step 4: 运行测试确认通过**

运行: `venv\\Scripts\\python.exe -m pytest tests/runtime/test_domain_models.py -v`
预期: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add apps/py-runtime/src/domain/models/project.py apps/py-runtime/src/domain/models/__init__.py tests/runtime/test_domain_models.py
git commit -m "feat: 添加 Project SQLAlchemy 模型"
```

---

### Task 3: ScriptVersion 和 StoryboardVersion 模型

**Files:**
- Create: `apps/py-runtime/src/domain/models/script.py`
- Create: `apps/py-runtime/src/domain/models/storyboard.py`
- Modify: `apps/py-runtime/src/domain/models/__init__.py`
- Test: `tests/runtime/test_domain_models.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/runtime/test_domain_models.py （追加）
from domain.models.script import ScriptVersion
from domain.models.storyboard import StoryboardVersion


def test_script_version_table_and_composite_pk():
    assert ScriptVersion.__tablename__ == "script_versions"
    pk_cols = [col.name for col in ScriptVersion.__table__.primary_key.columns]
    assert pk_cols == ["project_id", "revision"]


def test_storyboard_version_table_and_composite_pk():
    assert StoryboardVersion.__tablename__ == "storyboard_versions"
    pk_cols = [col.name for col in StoryboardVersion.__table__.primary_key.columns]
    assert pk_cols == ["project_id", "revision"]


def test_script_version_foreign_key_to_project():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        project = Project(
            id="p1", name="项目", description="", status="active",
            current_script_version=1, current_storyboard_version=0,
            created_at="2026-04-13T00:00:00Z",
            updated_at="2026-04-13T00:00:00Z",
            last_accessed_at="2026-04-13T00:00:00Z",
        )
        script = ScriptVersion(
            project_id="p1", revision=1, source="manual",
            content="脚本内容", created_at="2026-04-13T00:00:00Z",
        )
        session.add_all([project, script])
        session.commit()

        loaded = session.query(ScriptVersion).filter_by(project_id="p1", revision=1).one()
        assert loaded.content == "脚本内容"
```

- [ ] **Step 2: 运行测试确认失败**

运行: `venv\\Scripts\\python.exe -m pytest tests/runtime/test_domain_models.py::test_script_version_table_and_composite_pk -v`
预期: FAIL

- [ ] **Step 3: 实现 ScriptVersion 和 StoryboardVersion 模型**

```python
# apps/py-runtime/src/domain/models/script.py
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class ScriptVersion(Base):
    """脚本版本，按 (project_id, revision) 复合主键。"""

    __tablename__ = "script_versions"

    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True,
    )
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_job_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("ai_job_records.id", ondelete="SET NULL"), nullable=True,
    )
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
```

```python
# apps/py-runtime/src/domain/models/storyboard.py
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class StoryboardVersion(Base):
    """分镜版本，按 (project_id, revision) 复合主键。"""

    __tablename__ = "storyboard_versions"

    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True,
    )
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    based_on_script_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    scenes_json: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_job_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("ai_job_records.id", ondelete="SET NULL"), nullable=True,
    )
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
```

更新 `__init__.py` 增加导出。

- [ ] **Step 4: 运行测试确认通过**

运行: `venv\\Scripts\\python.exe -m pytest tests/runtime/test_domain_models.py -v`
预期: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add apps/py-runtime/src/domain/models/script.py apps/py-runtime/src/domain/models/storyboard.py apps/py-runtime/src/domain/models/__init__.py tests/runtime/test_domain_models.py
git commit -m "feat: 添加 ScriptVersion 和 StoryboardVersion 模型"
```

---

### Task 4: AIJobRecord、AICapabilityConfig、AIProviderSetting 模型

**Files:**
- Create: `apps/py-runtime/src/domain/models/ai_job.py`
- Create: `apps/py-runtime/src/domain/models/ai_capability.py`
- Modify: `apps/py-runtime/src/domain/models/__init__.py`
- Test: `tests/runtime/test_domain_models.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/runtime/test_domain_models.py （追加）
from domain.models.ai_job import AIJobRecord
from domain.models.ai_capability import AICapabilityConfig, AIProviderSetting


def test_ai_job_record_table():
    assert AIJobRecord.__tablename__ == "ai_job_records"


def test_ai_capability_config_table():
    assert AICapabilityConfig.__tablename__ == "ai_capability_configs"


def test_ai_provider_setting_table():
    assert AIProviderSetting.__tablename__ == "ai_provider_settings"


def test_ai_tables_created_in_memory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "ai_job_records" in tables
    assert "ai_capability_configs" in tables
    assert "ai_provider_settings" in tables
```

- [ ] **Step 2: 运行测试确认失败**
- [ ] **Step 3: 实现三个模型**

```python
# apps/py-runtime/src/domain/models/ai_job.py
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class AIJobRecord(Base):
    """AI 调用记录。"""

    __tablename__ = "ai_job_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True,
    )
    capability_id: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    completed_at: Mapped[str | None] = mapped_column(Text, nullable=True)
```

```python
# apps/py-runtime/src/domain/models/ai_capability.py
from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class AICapabilityConfig(Base):
    """AI 能力配置。"""

    __tablename__ = "ai_capability_configs"

    capability_id: Mapped[str] = mapped_column(String, primary_key=True)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    agent_role: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class AIProviderSetting(Base):
    """AI Provider 配置。"""

    __tablename__ = "ai_provider_settings"

    provider_id: Mapped[str] = mapped_column(String, primary_key=True)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
```

- [ ] **Step 4: 运行测试确认通过**
- [ ] **Step 5: 提交**

```bash
git add apps/py-runtime/src/domain/models/ai_job.py apps/py-runtime/src/domain/models/ai_capability.py apps/py-runtime/src/domain/models/__init__.py tests/runtime/test_domain_models.py
git commit -m "feat: 添加 AI 相关 Domain 模型"
```

---

### Task 5: LicenseGrant、SystemConfig、SessionContext 模型

**Files:**
- Create: `apps/py-runtime/src/domain/models/license.py`
- Create: `apps/py-runtime/src/domain/models/system_config.py`
- Modify: `apps/py-runtime/src/domain/models/__init__.py`
- Test: `tests/runtime/test_domain_models.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/runtime/test_domain_models.py （追加）
from domain.models.license import LicenseGrant
from domain.models.system_config import SystemConfig, SessionContext


def test_license_grant_table():
    assert LicenseGrant.__tablename__ == "license_grant"


def test_license_grant_columns_match_migration_3():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("license_grant")}
    expected = {
        "id", "active", "restricted_mode", "machine_id", "machine_bound",
        "activation_mode", "masked_code", "activated_at",
        "machine_code", "license_type", "signed_payload",
    }
    assert expected == columns


def test_system_config_table():
    assert SystemConfig.__tablename__ == "system_config"


def test_session_context_table():
    assert SessionContext.__tablename__ == "session_context"
```

- [ ] **Step 2: 运行测试确认失败**
- [ ] **Step 3: 实现三个模型**

```python
# apps/py-runtime/src/domain/models/license.py
from __future__ import annotations

from sqlalchemy import Integer, String, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class LicenseGrant(Base):
    """许可证授权状态。"""

    __tablename__ = "license_grant"
    __table_args__ = (CheckConstraint("id = 1"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    active: Mapped[int] = mapped_column(Integer, nullable=False)
    restricted_mode: Mapped[int] = mapped_column(Integer, nullable=False)
    machine_id: Mapped[str] = mapped_column(Text, nullable=False)
    machine_bound: Mapped[int] = mapped_column(Integer, nullable=False)
    activation_mode: Mapped[str] = mapped_column(Text, nullable=False)
    masked_code: Mapped[str] = mapped_column(Text, nullable=False)
    activated_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    machine_code: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    license_type: Mapped[str] = mapped_column(Text, nullable=False, server_default="perpetual")
    signed_payload: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
```

```python
# apps/py-runtime/src/domain/models/system_config.py
from __future__ import annotations

from sqlalchemy import Integer, String, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from domain.models.base import Base


class SystemConfig(Base):
    """系统配置单例。"""

    __tablename__ = "system_config"
    __table_args__ = (CheckConstraint("id = 1"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)


class SessionContext(Base):
    """会话上下文单例。"""

    __tablename__ = "session_context"
    __table_args__ = (CheckConstraint("id = 1"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    current_project_id: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[str] = mapped_column(Text, nullable=False)
```

- [ ] **Step 4: 运行测试确认通过**
- [ ] **Step 5: 提交**

```bash
git add apps/py-runtime/src/domain/models/license.py apps/py-runtime/src/domain/models/system_config.py apps/py-runtime/src/domain/models/__init__.py tests/runtime/test_domain_models.py
git commit -m "feat: 添加 License、SystemConfig、SessionContext 模型"
```

---

### Task 6: SQLAlchemy Engine 工厂与 Session 管理

**Files:**
- Create: `apps/py-runtime/src/persistence/engine.py`
- Modify: `apps/py-runtime/src/persistence/__init__.py`
- Test: `tests/runtime/test_domain_models.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/runtime/test_domain_models.py （追加）
from pathlib import Path
import tempfile

from persistence.engine import create_runtime_engine, create_session_factory


def test_engine_creates_sqlite_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        engine = create_runtime_engine(db_path)
        assert engine is not None
        assert "sqlite" in str(engine.url)


def test_session_factory_produces_usable_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        engine = create_runtime_engine(db_path)
        Base.metadata.create_all(engine)
        SessionFactory = create_session_factory(engine)
        with SessionFactory() as session:
            session.execute(session.bind.dialect.dbapi.connect(":memory:").execute("SELECT 1") if False else __import__("sqlalchemy").text("SELECT 1"))
```

- [ ] **Step 2: 运行测试确认失败**
- [ ] **Step 3: 实现 engine 工厂**

```python
# apps/py-runtime/src/persistence/engine.py
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_runtime_engine(database_path: Path) -> Engine:
    """创建 SQLAlchemy Engine，启用 SQLite foreign_keys。"""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{database_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """创建 Session 工厂。"""
    return sessionmaker(bind=engine, expire_on_commit=False)
```

- [ ] **Step 4: 运行测试确认通过**
- [ ] **Step 5: 提交**

```bash
git add apps/py-runtime/src/persistence/engine.py apps/py-runtime/src/persistence/__init__.py tests/runtime/test_domain_models.py
git commit -m "feat: 添加 SQLAlchemy Engine 工厂与 Session 管理"
```

---

### Task 7: Alembic 初始化与初始 Migration

**Files:**
- Create: `apps/py-runtime/alembic.ini`
- Create: `apps/py-runtime/alembic/env.py`
- Create: `apps/py-runtime/alembic/script.py.mako`
- Create: `apps/py-runtime/alembic/versions/0001_initial_schema.py`

- [ ] **Step 1: 初始化 Alembic 目录**

运行: `cd apps/py-runtime && venv\\Scripts\\python.exe -m alembic init alembic`
（如果已存在则跳过）

- [ ] **Step 2: 配置 `alembic.ini` 指向 SQLite**

修改 `alembic.ini` 中 `sqlalchemy.url` 为占位，实际由 `env.py` 动态设置。

- [ ] **Step 3: 配置 `alembic/env.py` 导入 Domain Models**

```python
# apps/py-runtime/alembic/env.py
from __future__ import annotations

import sys
from pathlib import Path

# 确保 src 在 Python 路径中
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from alembic import context
from sqlalchemy import engine_from_config, pool

from domain.models import Base  # 导入所有模型以注册 metadata

target_metadata = Base.metadata

# ... 标准 Alembic run_migrations_offline / run_migrations_online
```

- [ ] **Step 4: 生成初始 migration**

运行: `cd apps/py-runtime && venv\\Scripts\\python.exe -m alembic revision --autogenerate -m "initial schema"`

验证生成的 migration 包含所有 8 张表。

- [ ] **Step 5: 提交**

```bash
git add apps/py-runtime/alembic.ini apps/py-runtime/alembic/
git commit -m "feat: 初始化 Alembic 并生成初始 migration"
```

---

### Task 8: Repository 层迁移到 SQLAlchemy（DashboardRepository 示范）

**Files:**
- Modify: `apps/py-runtime/src/repositories/dashboard_repository.py`
- Modify: `apps/py-runtime/src/app/factory.py`
- Test: `tests/runtime/test_repository_orm.py`

- [ ] **Step 1: 编写 ORM 版 DashboardRepository 的失败测试**

```python
# tests/runtime/test_repository_orm.py
from __future__ import annotations

import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from domain.models import Base, Project
from persistence.engine import create_runtime_engine, create_session_factory
from repositories.dashboard_repository import DashboardRepository


def _make_session_factory():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        engine = create_runtime_engine(db_path)
        Base.metadata.create_all(engine)
        return create_session_factory(engine), tmpdir


def test_dashboard_create_project_orm():
    session_factory, tmpdir = _make_session_factory()
    repo = DashboardRepository(session_factory=session_factory)
    result = repo.create_project("测试", "描述")
    assert result["name"] == "测试"
    assert result["id"] is not None
```

- [ ] **Step 2: 运行测试确认失败**

当前 `DashboardRepository.__init__` 接收 `database_path`，不接收 `session_factory`，所以会失败。

- [ ] **Step 3: 将 DashboardRepository 迁移到 SQLAlchemy Session**

重构 `DashboardRepository` 构造函数接收 `session_factory`，内部方法改为通过 `Session` 操作 `Project` 模型。保持返回的字典结构不变，确保服务层零改动。

- [ ] **Step 4: 更新 `factory.py` 注入 session_factory**

在 `create_app()` 中创建 engine 和 session_factory，传给各 Repository。

- [ ] **Step 5: 运行全部测试确认通过**

运行: `venv\\Scripts\\python.exe -m pytest tests/ -q`
预期: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add apps/py-runtime/src/repositories/dashboard_repository.py apps/py-runtime/src/app/factory.py tests/runtime/test_repository_orm.py
git commit -m "refactor: DashboardRepository 迁移到 SQLAlchemy ORM"
```

---

### Task 9: 剩余 Repository 批量迁移

**Files:**
- Modify: `apps/py-runtime/src/repositories/script_repository.py`
- Modify: `apps/py-runtime/src/repositories/storyboard_repository.py`
- Modify: `apps/py-runtime/src/repositories/ai_capability_repository.py`
- Modify: `apps/py-runtime/src/repositories/ai_job_repository.py`
- Modify: `apps/py-runtime/src/repositories/license_repository.py`
- Modify: `apps/py-runtime/src/repositories/system_config_repository.py`
- Modify: `apps/py-runtime/src/app/factory.py`

按 Task 8 同样模式，逐个将每个 Repository 从原生 `sqlite3.Connection` 迁移到 `session_factory`。

每个 Repository 迁移后立即运行全部测试确认无回归：

- [ ] **Step 1: 迁移 ScriptRepository**
- [ ] **Step 2: 运行测试确认通过**
- [ ] **Step 3: 迁移 StoryboardRepository**
- [ ] **Step 4: 运行测试确认通过**
- [ ] **Step 5: 迁移 AICapabilityRepository**
- [ ] **Step 6: 运行测试确认通过**
- [ ] **Step 7: 迁移 AIJobRepository**
- [ ] **Step 8: 运行测试确认通过**
- [ ] **Step 9: 迁移 LicenseRepository**
- [ ] **Step 10: 运行测试确认通过**
- [ ] **Step 11: 迁移 SystemConfigRepository**
- [ ] **Step 12: 运行测试确认通过**
- [ ] **Step 13: 从 factory.py 移除旧 `database_path` 直连逻辑**
- [ ] **Step 14: 运行全部测试（前端 + Runtime + 契约）确认通过**

运行:
```bash
npm --prefix apps/desktop run test
venv\\Scripts\\python.exe -m pytest tests/runtime -q
venv\\Scripts\\python.exe -m pytest tests/contracts -q
```

- [ ] **Step 15: 提交**

```bash
git add apps/py-runtime/src/repositories/ apps/py-runtime/src/app/factory.py
git commit -m "refactor: 全部 Repository 迁移到 SQLAlchemy ORM"
```

---

### Task 10: 清理与最终验证

**Files:**
- Modify: `apps/py-runtime/src/persistence/sqlite.py` — 标记旧 `connect_sqlite` 为 deprecated 或移除
- Modify: `apps/py-runtime/src/persistence/migrations.py` — 保留文件但添加注释说明已由 Alembic 接管

- [ ] **Step 1: 清理 persistence 旧入口**

如果所有 Repository 已不再直接调用 `connect_sqlite`，将其标记为已废弃。`migrations.py` 保留作为历史参考，头部添加注释。

- [ ] **Step 2: 运行一键启动确认桌面应用正常**

运行: `npm run app:dev`
验证: 首启流程、授权、创建项目、脚本生成、分镜生成全链路正常。

- [ ] **Step 3: 运行全部测试套件**

```bash
npm --prefix apps/desktop run test
venv\\Scripts\\python.exe -m pytest tests/ -q
```

- [ ] **Step 4: 提交**

```bash
git add apps/py-runtime/src/persistence/
git commit -m "chore: 标记旧 SQLite 直连为已废弃，迁移由 Alembic 管理"
```
