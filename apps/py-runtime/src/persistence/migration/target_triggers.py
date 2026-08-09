from __future__ import annotations

TriggerContract = tuple[str, set[str], str]

# 语义片段便于审计，规范化 SQL 哈希负责拒绝任何永假条件或额外分支。
P0_REQUIRED_TRIGGERS: dict[str, TriggerContract] = {
    "trg_knowledge_sources_account_base_insert": (
        "knowledge_sources",
        {
            "before insert on knowledge_sources",
            "base.id = new.knowledge_base_id",
            "base.account_id = new.account_id",
            "raise(abort, 'knowledge_source_account_mismatch')",
        },
        "8ec0181f3e1d9890407bd0937e04f4602d2fabd86360712aafb04e8f2ff8ad37",
    ),
    "trg_knowledge_sources_account_base_update": (
        "knowledge_sources",
        {
            "before update of account_id, knowledge_base_id on knowledge_sources",
            "base.id = new.knowledge_base_id",
            "base.account_id = new.account_id",
            "raise(abort, 'knowledge_source_account_mismatch')",
        },
        "55edc38f59fe963b1fc4382139f7a832fb9d9680b8332392e3a15823e95924cf",
    ),
    "trg_execution_bindings_scope_insert": (
        "execution_bindings",
        {
            "before insert on execution_bindings",
            "workspace.id = new.device_workspace_id",
            "workspace.account_id = new.account_id",
            "browser.id = new.browser_instance_id",
            "browser.account_id = new.account_id",
            "browser.workspace_id = new.device_workspace_id",
            "raise(abort, 'execution_binding_account_mismatch')",
        },
        "fc7652feda3a8a59dbb43a2c206d270836376ea0c2975acb8a4649e3547082d9",
    ),
    "trg_execution_bindings_scope_update": (
        "execution_bindings",
        {
            "before update of account_id, device_workspace_id, "
            "browser_instance_id on execution_bindings",
            "workspace.account_id = new.account_id",
            "browser.account_id = new.account_id",
            "connection.active_execution_binding_id = old.id",
            "new.browser_instance_id is null",
            "connection.account_id <> new.account_id",
            "raise(abort, 'execution_binding_account_mismatch')",
        },
        "1f7c68b2bf30b5659ebb044c887af6afa876e7c066ce13cb9dd65279f07bf98c",
    ),
    "trg_device_workspaces_scope_update": (
        "device_workspaces",
        {
            "before update of account_id on device_workspaces",
            "browser.workspace_id = old.id",
            "new.account_id is null",
            "browser.account_id is not null",
            "new.account_id is not null",
            "browser.account_id is null",
            "browser.account_id <> new.account_id",
            "binding.device_workspace_id = old.id",
            "binding.account_id <> new.account_id",
            "raise(abort, 'device_workspace_account_mismatch')",
        },
        "0bd00d77537f3b02731b9665ed2f776aa867ee996f6846a7f0f4dbcf8137af3a",
    ),
    "trg_browser_instances_scope_insert": (
        "browser_instances",
        {
            "before insert on browser_instances",
            "workspace.id = new.workspace_id",
            "workspace.account_id is null",
            "new.account_id is null",
            "workspace.account_id is not null",
            "workspace.account_id = new.account_id",
            "raise(abort, 'browser_instance_account_mismatch')",
        },
        "533ca28886f39e08796cb746caf123d276d1225c61fe3dc80c5cbcc3632b08e7",
    ),
    "trg_browser_instances_scope_update": (
        "browser_instances",
        {
            "before update of account_id, workspace_id on browser_instances",
            "workspace.account_id is null",
            "new.account_id is null",
            "workspace.account_id is not null",
            "workspace.account_id = new.account_id",
            "binding.browser_instance_id = old.id",
            "binding.account_id <> new.account_id",
            "binding.device_workspace_id <> new.workspace_id",
            "raise(abort, 'browser_instance_account_mismatch')",
        },
        "17ffff337ce7f0284b0e27e8c51e38d96e03de870e97777f1c1a8cf7df91bdcd",
    ),
    "trg_account_connections_binding_insert": (
        "account_connections",
        {
            "before insert on account_connections",
            "new.active_execution_binding_id is not null",
            "binding.id = new.active_execution_binding_id",
            "binding.account_id = new.account_id",
            "workspace.account_id = new.account_id",
            "browser.account_id = new.account_id",
            "browser.workspace_id = workspace.id",
            "raise(abort, 'account_connection_binding_mismatch')",
        },
        "4d5df38b04ca1f9d45b37dda129192a098f1946f3e86b6af85893ddf9a7f1dfd",
    ),
    "trg_account_connections_binding_update": (
        "account_connections",
        {
            "before update of account_id, active_execution_binding_id "
            "on account_connections",
            "new.active_execution_binding_id is not null",
            "binding.id = new.active_execution_binding_id",
            "binding.account_id = new.account_id",
            "workspace.account_id = new.account_id",
            "browser.account_id = new.account_id",
            "browser.workspace_id = workspace.id",
            "raise(abort, 'account_connection_binding_mismatch')",
        },
        "f47b1fb0f1aaa21a76c8d0a153e2731941974053ed47d40737f301179bf87f1b",
    ),
    "trg_knowledge_snapshots_scope_insert": (
        "knowledge_snapshots",
        {
            "before insert on knowledge_snapshots",
            "base.id = new.knowledge_base_id",
            "base.account_id = new.account_id",
            "profile.id = new.positioning_profile_id",
            "profile.account_id = new.account_id",
            "raise(abort, 'knowledge_snapshot_account_mismatch')",
        },
        "23ba2b7ce74e052df399c53c9f8830709341752adabf7675d30ca05933ec2591",
    ),
    "trg_knowledge_snapshots_scope_update": (
        "knowledge_snapshots",
        {
            "before update of account_id, knowledge_base_id, "
            "positioning_profile_id on knowledge_snapshots",
            "base.account_id = new.account_id",
            "profile.account_id = new.account_id",
            "raise(abort, 'knowledge_snapshot_account_mismatch')",
        },
        "b64ad1b75f3b9fa3cec07374c58c0242b5ef6545e4f5c529fb453b251ccc07d4",
    ),
    "trg_account_knowledge_bases_account_update": (
        "account_knowledge_bases",
        {
            "before update of account_id on account_knowledge_bases",
            "source.knowledge_base_id = old.id",
            "source.account_id <> new.account_id",
            "snapshot.knowledge_base_id = old.id",
            "snapshot.account_id <> new.account_id",
            "raise(abort, 'knowledge_base_account_mismatch')",
        },
        "72f8ae3472ad23c45c2091231b2a1704f4609cdc0e80eedad3343e68dbb783a4",
    ),
    "trg_positioning_profiles_account_update": (
        "positioning_profiles",
        {
            "before update of account_id on positioning_profiles",
            "snapshot.positioning_profile_id = old.id",
            "snapshot.account_id <> new.account_id",
            "raise(abort, 'positioning_profile_account_mismatch')",
        },
        "eb719f99cfbd9346a40339a54c57e7e21e6c0f2a5545ff3290b114042883039a",
    ),
}
