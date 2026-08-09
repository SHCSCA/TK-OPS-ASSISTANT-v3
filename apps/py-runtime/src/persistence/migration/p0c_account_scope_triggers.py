from __future__ import annotations

# 0019 降级后必须恢复 0018 已有的三条隔离触发器。
P0B_ACCOUNT_SCOPE_TRIGGERS = {
    "trg_knowledge_sources_account_base_insert": """
        CREATE TRIGGER trg_knowledge_sources_account_base_insert
        BEFORE INSERT ON knowledge_sources
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1
            FROM account_knowledge_bases AS base
            WHERE base.id = NEW.knowledge_base_id
              AND base.account_id = NEW.account_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'KNOWLEDGE_SOURCE_ACCOUNT_MISMATCH');
        END
    """,
    "trg_knowledge_sources_account_base_update": """
        CREATE TRIGGER trg_knowledge_sources_account_base_update
        BEFORE UPDATE OF account_id, knowledge_base_id ON knowledge_sources
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1
            FROM account_knowledge_bases AS base
            WHERE base.id = NEW.knowledge_base_id
              AND base.account_id = NEW.account_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'KNOWLEDGE_SOURCE_ACCOUNT_MISMATCH');
        END
    """,
    "trg_account_knowledge_bases_account_update": """
        CREATE TRIGGER trg_account_knowledge_bases_account_update
        BEFORE UPDATE OF account_id ON account_knowledge_bases
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1
            FROM knowledge_sources AS source
            WHERE source.knowledge_base_id = OLD.id
              AND source.account_id <> NEW.account_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'KNOWLEDGE_BASE_ACCOUNT_MISMATCH');
        END
    """,
}

# 该迁移专用 SQL 与 0019 同步冻结，避免账号隔离规则分散为多个版本。
P0C_ACCOUNT_SCOPE_TRIGGERS = {
    **P0B_ACCOUNT_SCOPE_TRIGGERS,
    "trg_execution_bindings_scope_insert": """
        CREATE TRIGGER trg_execution_bindings_scope_insert
        BEFORE INSERT ON execution_bindings
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1 FROM device_workspaces AS workspace
            WHERE workspace.id = NEW.device_workspace_id
              AND workspace.account_id = NEW.account_id
        ) OR (
            NEW.browser_instance_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM browser_instances AS browser
                WHERE browser.id = NEW.browser_instance_id
                  AND browser.account_id = NEW.account_id
                  AND browser.workspace_id = NEW.device_workspace_id
            )
        )
        BEGIN
            SELECT RAISE(ABORT, 'EXECUTION_BINDING_ACCOUNT_MISMATCH');
        END
    """,
    "trg_execution_bindings_scope_update": """
        CREATE TRIGGER trg_execution_bindings_scope_update
        BEFORE UPDATE OF account_id, device_workspace_id, browser_instance_id
        ON execution_bindings
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1 FROM device_workspaces AS workspace
            WHERE workspace.id = NEW.device_workspace_id
              AND workspace.account_id = NEW.account_id
        ) OR (
            NEW.browser_instance_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM browser_instances AS browser
                WHERE browser.id = NEW.browser_instance_id
                  AND browser.account_id = NEW.account_id
                  AND browser.workspace_id = NEW.device_workspace_id
            )
        ) OR EXISTS (
            SELECT 1 FROM account_connections AS connection
            WHERE connection.active_execution_binding_id = OLD.id
              AND (
                  NEW.browser_instance_id IS NULL
                  OR connection.account_id <> NEW.account_id
              )
        )
        BEGIN
            SELECT RAISE(ABORT, 'EXECUTION_BINDING_ACCOUNT_MISMATCH');
        END
    """,
    "trg_device_workspaces_scope_update": """
        CREATE TRIGGER trg_device_workspaces_scope_update
        BEFORE UPDATE OF account_id ON device_workspaces
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1 FROM browser_instances AS browser
            WHERE browser.workspace_id = OLD.id
              AND (
                  (
                      NEW.account_id IS NULL
                      AND browser.account_id IS NOT NULL
                  )
                  OR (
                      NEW.account_id IS NOT NULL
                      AND (
                          browser.account_id IS NULL
                          OR browser.account_id <> NEW.account_id
                      )
                  )
              )
        ) OR EXISTS (
            SELECT 1 FROM execution_bindings AS binding
            WHERE binding.device_workspace_id = OLD.id
              AND (
                  NEW.account_id IS NULL
                  OR binding.account_id <> NEW.account_id
              )
        )
        BEGIN
            SELECT RAISE(ABORT, 'DEVICE_WORKSPACE_ACCOUNT_MISMATCH');
        END
    """,
    "trg_browser_instances_scope_insert": """
        CREATE TRIGGER trg_browser_instances_scope_insert
        BEFORE INSERT ON browser_instances
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1 FROM device_workspaces AS workspace
            WHERE workspace.id = NEW.workspace_id
              AND (
                    (
                        workspace.account_id IS NULL
                        AND NEW.account_id IS NULL
                    )
                    OR (
                        workspace.account_id IS NOT NULL
                        AND workspace.account_id = NEW.account_id
                    )
              )
        )
        BEGIN
            SELECT RAISE(ABORT, 'BROWSER_INSTANCE_ACCOUNT_MISMATCH');
        END
    """,
    "trg_browser_instances_scope_update": """
        CREATE TRIGGER trg_browser_instances_scope_update
        BEFORE UPDATE OF account_id, workspace_id ON browser_instances
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1 FROM device_workspaces AS workspace
            WHERE workspace.id = NEW.workspace_id
              AND (
                    (
                        workspace.account_id IS NULL
                        AND NEW.account_id IS NULL
                    )
                    OR (
                        workspace.account_id IS NOT NULL
                        AND workspace.account_id = NEW.account_id
                    )
              )
        ) OR EXISTS (
            SELECT 1 FROM execution_bindings AS binding
            WHERE binding.browser_instance_id = OLD.id
              AND (
                  binding.account_id <> NEW.account_id
                  OR binding.device_workspace_id <> NEW.workspace_id
              )
        )
        BEGIN
            SELECT RAISE(ABORT, 'BROWSER_INSTANCE_ACCOUNT_MISMATCH');
        END
    """,
    "trg_account_connections_binding_insert": """
        CREATE TRIGGER trg_account_connections_binding_insert
        BEFORE INSERT ON account_connections
        FOR EACH ROW
        WHEN NEW.active_execution_binding_id IS NOT NULL
         AND NOT EXISTS (
            SELECT 1
            FROM execution_bindings AS binding
            JOIN device_workspaces AS workspace
              ON workspace.id = binding.device_workspace_id
            JOIN browser_instances AS browser
              ON browser.id = binding.browser_instance_id
            WHERE binding.id = NEW.active_execution_binding_id
              AND binding.account_id = NEW.account_id
              AND workspace.account_id = NEW.account_id
              AND browser.account_id = NEW.account_id
              AND browser.workspace_id = workspace.id
        )
        BEGIN
            SELECT RAISE(ABORT, 'ACCOUNT_CONNECTION_BINDING_MISMATCH');
        END
    """,
    "trg_account_connections_binding_update": """
        CREATE TRIGGER trg_account_connections_binding_update
        BEFORE UPDATE OF account_id, active_execution_binding_id
        ON account_connections
        FOR EACH ROW
        WHEN NEW.active_execution_binding_id IS NOT NULL
         AND NOT EXISTS (
            SELECT 1
            FROM execution_bindings AS binding
            JOIN device_workspaces AS workspace
              ON workspace.id = binding.device_workspace_id
            JOIN browser_instances AS browser
              ON browser.id = binding.browser_instance_id
            WHERE binding.id = NEW.active_execution_binding_id
              AND binding.account_id = NEW.account_id
              AND workspace.account_id = NEW.account_id
              AND browser.account_id = NEW.account_id
              AND browser.workspace_id = workspace.id
        )
        BEGIN
            SELECT RAISE(ABORT, 'ACCOUNT_CONNECTION_BINDING_MISMATCH');
        END
    """,
    "trg_knowledge_snapshots_scope_insert": """
        CREATE TRIGGER trg_knowledge_snapshots_scope_insert
        BEFORE INSERT ON knowledge_snapshots
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1 FROM account_knowledge_bases AS base
            WHERE base.id = NEW.knowledge_base_id
              AND base.account_id = NEW.account_id
        ) OR (
            NEW.positioning_profile_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM positioning_profiles AS profile
                WHERE profile.id = NEW.positioning_profile_id
                  AND profile.account_id = NEW.account_id
            )
        )
        BEGIN
            SELECT RAISE(ABORT, 'KNOWLEDGE_SNAPSHOT_ACCOUNT_MISMATCH');
        END
    """,
    "trg_knowledge_snapshots_scope_update": """
        CREATE TRIGGER trg_knowledge_snapshots_scope_update
        BEFORE UPDATE OF account_id, knowledge_base_id, positioning_profile_id
        ON knowledge_snapshots
        FOR EACH ROW
        WHEN NOT EXISTS (
            SELECT 1 FROM account_knowledge_bases AS base
            WHERE base.id = NEW.knowledge_base_id
              AND base.account_id = NEW.account_id
        ) OR (
            NEW.positioning_profile_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM positioning_profiles AS profile
                WHERE profile.id = NEW.positioning_profile_id
                  AND profile.account_id = NEW.account_id
            )
        )
        BEGIN
            SELECT RAISE(ABORT, 'KNOWLEDGE_SNAPSHOT_ACCOUNT_MISMATCH');
        END
    """,
    "trg_account_knowledge_bases_account_update": """
        CREATE TRIGGER trg_account_knowledge_bases_account_update
        BEFORE UPDATE OF account_id ON account_knowledge_bases
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1 FROM knowledge_sources AS source
            WHERE source.knowledge_base_id = OLD.id
              AND source.account_id <> NEW.account_id
        ) OR EXISTS (
            SELECT 1 FROM knowledge_snapshots AS snapshot
            WHERE snapshot.knowledge_base_id = OLD.id
              AND snapshot.account_id <> NEW.account_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'KNOWLEDGE_BASE_ACCOUNT_MISMATCH');
        END
    """,
    "trg_positioning_profiles_account_update": """
        CREATE TRIGGER trg_positioning_profiles_account_update
        BEFORE UPDATE OF account_id ON positioning_profiles
        FOR EACH ROW
        WHEN EXISTS (
            SELECT 1 FROM knowledge_snapshots AS snapshot
            WHERE snapshot.positioning_profile_id = OLD.id
              AND snapshot.account_id <> NEW.account_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'POSITIONING_PROFILE_ACCOUNT_MISMATCH');
        END
    """,
}
