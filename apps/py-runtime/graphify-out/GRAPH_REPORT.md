# Graph Report - apps/py-runtime  (2026-04-19)

## Corpus Check
- Corpus is ~42,698 words - fits in a single context window. You may not need a graph.

## Summary
- 1394 nodes · 3844 edges · 37 communities detected
- Extraction: 57% EXTRACTED · 43% INFERRED · 0% AMBIGUOUS · INFERRED: 1658 edges (avg confidence: 0.71)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_.get()  Base|.get() / Base]]
- [[_COMMUNITY_HTTPException  Exception  AccountService|HTTPException / Exception / AccountService]]
- [[_COMMUNITY_ok_response()  assets.py  _svc()|ok_response() / assets.py / _svc()]]
- [[_COMMUNITY_create_app()  UnavailableLicenseActivationAdapter  LicenseService|create_app() / UnavailableLicenseActivationAdapter / LicenseService]]
- [[_COMMUNITY_BaseModel  SettingsService  RenderService|BaseModel / SettingsService / RenderService]]
- [[_COMMUNITY_StoryboardService  ScriptService  .require_project()|StoryboardService / ScriptService / .require_project()]]
- [[_COMMUNITY_AICapabilityService  ai_capability_service.py  ProviderConnectivityError|AICapabilityService / ai_capability_service.py / ProviderConnectivityError]]
- [[_COMMUNITY_VideoDeconstructionService  TaskManager  _StageDefinition|VideoDeconstructionService / TaskManager / _StageDefinition]]
- [[_COMMUNITY_ProviderHTTPException  .generate_text()  AIJobRepository|ProviderHTTPException / .generate_text() / AIJobRepository]]
- [[_COMMUNITY_ReviewService  utc_now()  DashboardService|ReviewService / utc_now() / DashboardService]]
- [[_COMMUNITY_WorkspaceService  workspace.py  TimelineRepository|WorkspaceService / workspace.py / TimelineRepository]]
- [[_COMMUNITY_VoiceService  _BuiltinVoiceProfile  .generate_track()|VoiceService / _BuiltinVoiceProfile / .generate_track()]]
- [[_COMMUNITY_SubtitleService  _BuiltinSubtitleStyleTemplate  subtitles.py|SubtitleService / _BuiltinSubtitleStyleTemplate / subtitles.py]]
- [[_COMMUNITY_process_video_import_task()  .broadcast()  migrations.py|process_video_import_task() / .broadcast() / migrations.py]]
- [[_COMMUNITY_AutomationService  AutomationRepository  ._to_task_dto()|AutomationService / AutomationRepository / ._to_task_dto()]]
- [[_COMMUNITY_PromptTemplateService  PromptTemplateRepository  ._to_stored()|PromptTemplateService / PromptTemplateRepository / ._to_stored()]]
- [[_COMMUNITY_SearchService  .search()  search.py|SearchService / .search() / search.py]]
- [[_COMMUNITY_utc_now_iso()  BootstrapService  .runtime_selfcheck()|utc_now_iso() / BootstrapService / .runtime_selfcheck()]]
- [[_COMMUNITY_0001_initial_schema.py  upgrade()  initial schema  Revision ID 0001_initial_schema Revises Create Date 2026-|0001_initial_schema.py / upgrade() / initial schema  Revision ID: 0001_initial_schema Revises: Create Date: 2026-]]
- [[_COMMUNITY_0002_add_imported_videos.py  upgrade()  downgrade()|0002_add_imported_videos.py / upgrade() / downgrade()]]
- [[_COMMUNITY_0003_add_business_modules.py  upgrade()  downgrade()|0003_add_business_modules.py / upgrade() / downgrade()]]
- [[_COMMUNITY_0004_add_prompt_templates_and_video_stage_runs.py  upgrade()  downgrade()|0004_add_prompt_templates_and_video_stage_runs.py / upgrade() / downgrade()]]
- [[_COMMUNITY_0005_add_voice_profiles.py  upgrade()  downgrade()|0005_add_voice_profiles.py / upgrade() / downgrade()]]
- [[_COMMUNITY_0006_merge_runtime_heads.py  upgrade()  merge runtime migration heads  Revision ID 0006_merge_runtime_heads Revises|0006_merge_runtime_heads.py / upgrade() / merge runtime migration heads  Revision ID: 0006_merge_runtime_heads Revises:]]
- [[_COMMUNITY_当前职责  README  本地运行（使用项目根 venv）|当前职责 / README / 本地运行（使用项目根 venv）]]
- [[_COMMUNITY_main.py  main()|main.py / main()]]
- [[_COMMUNITY_create_app()  __init__.py|create_app() / __init__.py]]
- [[_COMMUNITY___init__.py  Developer-only Runtime helpers.|__init__.py / Developer-only Runtime helpers.]]
- [[_COMMUNITY___init__.py|__init__.py]]
- [[_COMMUNITY___init__.py|__init__.py]]
- [[_COMMUNITY___init__.py|__init__.py]]
- [[_COMMUNITY___init__.py|__init__.py]]
- [[_COMMUNITY___init__.py|__init__.py]]
- [[_COMMUNITY___init__.py|__init__.py]]
- [[_COMMUNITY___init__.py|__init__.py]]
- [[_COMMUNITY_video_tasks.py|video_tasks.py]]
- [[_COMMUNITY___init__.py|__init__.py]]

## God Nodes (most connected - your core abstractions)
1. `ok_response()` - 163 edges
2. `create_app()` - 55 edges
3. `UnavailableLicenseActivationAdapter` - 51 edges
4. `VoiceService` - 50 edges
5. `SettingsService` - 46 edges
6. `WorkspaceService` - 46 edges
7. `AccountService` - 45 edges
8. `AssetService` - 43 edges
9. `VideoDeconstructionService` - 43 edges
10. `Base` - 40 edges

## Surprising Connections (you probably didn't know these)
- `OpenAITTSAdapter` --uses--> `TTSRequest`  [INFERRED]
  G:\AI\TK-OPS-ASSISTANT-V3\apps\py-runtime\src\ai\providers\tts_openai.py → G:\AI\TK-OPS-ASSISTANT-V3\apps\py-runtime\src\ai\providers\base.py
- `_BuiltinVoiceProfile` --uses--> `TTSResponse`  [INFERRED]
  G:\AI\TK-OPS-ASSISTANT-V3\apps\py-runtime\src\services\voice_service.py → G:\AI\TK-OPS-ASSISTANT-V3\apps\py-runtime\src\ai\providers\base.py
- `VoiceService` --uses--> `TTSResponse`  [INFERRED]
  G:\AI\TK-OPS-ASSISTANT-V3\apps\py-runtime\src\services\voice_service.py → G:\AI\TK-OPS-ASSISTANT-V3\apps\py-runtime\src\ai\providers\base.py
- `get_ai_provider_catalog()` --calls--> `ok_response()`  [INFERRED]
  G:\AI\TK-OPS-ASSISTANT-V3\apps\py-runtime\src\api\routes\ai_providers.py → G:\AI\TK-OPS-ASSISTANT-V3\apps\py-runtime\src\schemas\envelope.py
- `get_ai_provider_models()` --calls--> `ok_response()`  [INFERRED]
  G:\AI\TK-OPS-ASSISTANT-V3\apps\py-runtime\src\api\routes\ai_providers.py → G:\AI\TK-OPS-ASSISTANT-V3\apps\py-runtime\src\schemas\envelope.py

## Hyperedges (group relationships)
- **README topics** — doc_g_ai_tk_ops_assistant_v3_apps_py_runtime_readme_md, readme, readme, readme [INFERRED 0.70]

## Communities

### Community 0 - ".get() / Base"
Cohesion: 0.02
Nodes (62): Account, AccountGroup, AccountGroupMember, AccountRepository, 更新 updated_at（用于 refresh-stats V1 占位）, _utc_now(), AICapabilityConfig, AIProviderSetting (+54 more)

### Community 1 - "HTTPException / Exception / AccountService"
Cohesion: 0.04
Nodes (49): AccountService, _mask_sensitive_json(), _mask_value(), _utc_now(), AccountBindingDto, AccountBindingUpsertInput, AccountCreateInput, AccountDto (+41 more)

### Community 2 - "ok_response() / assets.py / _svc()"
Cohesion: 0.03
Nodes (139): add_group_member(), create_account(), create_account_group(), delete_account(), delete_account_group(), get_account(), list_account_groups(), list_accounts() (+131 more)

### Community 3 - "create_app() / UnavailableLicenseActivationAdapter / LicenseService"
Cohesion: 0.04
Nodes (55): load_runtime_config(), _load_runtime_version(), RuntimeConfig, create_runtime_engine(), create_session_factory(), _has_blocking_legacy_asset_columns(), initialize_domain_schema(), _rebuild_legacy_asset_table() (+47 more)

### Community 4 - "BaseModel / SettingsService / RenderService"
Cohesion: 0.06
Nodes (50): BaseModel, log_event(), ExportProfile, RenderService, CancelRenderResultDto, DiskUsageSnapshotDto, ExportProfileCreateInput, ExportProfileDto (+42 more)

### Community 5 - "StoryboardService / ScriptService / .require_project()"
Cohesion: 0.06
Nodes (39): _emit_script_stream_event(), _parse_segment_index(), _parse_title_variants(), _pick_segment_rewrite(), ScriptService, _split_lines(), AIJobRecordDto, generate_script() (+31 more)

### Community 6 - "AICapabilityService / ai_capability_service.py / ProviderConnectivityError"
Cohesion: 0.07
Nodes (49): AICapabilityConfigDto, AICapabilityConfigListInput, AICapabilityModelOptionDto, AICapabilitySettingsDto, AICapabilitySupportItemDto, AICapabilitySupportMatrixDto, AIModelCatalogItemDto, AIModelCatalogRefreshResultDto (+41 more)

### Community 7 - "VideoDeconstructionService / TaskManager / _StageDefinition"
Cohesion: 0.05
Nodes (24): ImportedVideoRepository, 管理内存态长任务生命周期与 WebSocket 进度广播。, TaskInfo, TaskManager, _utc_now(), get_task(), list_tasks(), ValueError (+16 more)

### Community 8 - "ProviderHTTPException / .generate_text() / AIJobRepository"
Cohesion: 0.06
Nodes (37): ABC, AIJobRepository, StoredAIJobRecord, _utc_now(), AITextGenerationService, GeneratedTextResult, _render_template(), AnthropicMessagesTextGenerationAdapter (+29 more)

### Community 9 - "ReviewService / utc_now() / DashboardService"
Cohesion: 0.07
Nodes (25): create_project(), CreateProjectInput, CurrentProjectContextDto, DashboardSummaryDto, get_current_project_context(), get_dashboard_service(), get_dashboard_summary(), ProjectSummaryDto (+17 more)

### Community 10 - "WorkspaceService / workspace.py / TimelineRepository"
Cohesion: 0.08
Nodes (18): generate_uuid(), TimelineRepository, ClipMoveInput, ClipReplaceInput, ClipTrimInput, WorkspaceService, TimelineClipDto, TimelineCreateInput (+10 more)

### Community 11 - "VoiceService / _BuiltinVoiceProfile / .generate_track()"
Cohesion: 0.11
Nodes (14): TTSRequest, VoiceProfileRepository, _BuiltinVoiceProfile, VoiceService, VoiceProfileCreateInput, VoiceProfileDto, VoiceSegmentRegenerateInput, VoiceTrackDto (+6 more)

### Community 12 - "SubtitleService / _BuiltinSubtitleStyleTemplate / subtitles.py"
Cohesion: 0.1
Nodes (15): configure_logging(), JsonLogFormatter, _resolve_level(), _BuiltinSubtitleStyleTemplate, SubtitleService, SubtitleExportDto, SubtitleExportInput, SubtitleSegmentDto (+7 more)

### Community 13 - "process_video_import_task() / .broadcast() / migrations.py"
Cohesion: 0.08
Nodes (22): _database_url(), run_migrations_offline(), run_migrations_online(), FfprobeResult, parse_ffprobe_output(), _parse_frame_rate(), probe_video(), _to_float() (+14 more)

### Community 14 - "AutomationService / AutomationRepository / ._to_task_dto()"
Cohesion: 0.1
Nodes (11): AutomationTask, AutomationTaskCreateInput, AutomationTaskDto, AutomationTaskRuleDto, AutomationTaskRuleInput, AutomationTaskRun, AutomationTaskRunDto, AutomationTaskUpdateInput (+3 more)

### Community 15 - "PromptTemplateService / PromptTemplateRepository / ._to_stored()"
Cohesion: 0.12
Nodes (12): PromptTemplateRepository, StoredPromptTemplate, _utc_now(), PromptTemplateService, create_prompt_template(), delete_prompt_template(), get_prompt_template_service(), list_prompt_templates() (+4 more)

### Community 16 - "SearchService / .search() / search.py"
Cohesion: 0.14
Nodes (10): GlobalSearchResultDto, search_global(), SearchAccountResultDto, SearchAssetResultDto, SearchProjectResultDto, SearchScriptResultDto, SearchTaskResultDto, SearchWorkspaceResultDto (+2 more)

### Community 17 - "utc_now_iso() / BootstrapService / .runtime_selfcheck()"
Cohesion: 0.26
Nodes (7): BootstrapDirectoryItemDto, BootstrapDirectoryReportDto, RuntimeSelfCheckItemDto, RuntimeSelfCheckReportDto, BootstrapService, _check_port_listening(), utc_now_iso()

### Community 18 - "0001_initial_schema.py / upgrade() / initial schema  Revision ID: 0001_initial_schema Revises: Create Date: 2026-"
Cohesion: 0.5
Nodes (1): initial schema  Revision ID: 0001_initial_schema Revises: Create Date: 2026-

### Community 19 - "0002_add_imported_videos.py / upgrade() / downgrade()"
Cohesion: 0.5
Nodes (1): add imported videos  Revision ID: 0002_add_imported_videos Revises: 0001_init

### Community 20 - "0003_add_business_modules.py / upgrade() / downgrade()"
Cohesion: 0.5
Nodes (1): add business modules  Revision ID: 0003_add_business_modules Revises: 0002_ad

### Community 21 - "0004_add_prompt_templates_and_video_stage_runs.py / upgrade() / downgrade()"
Cohesion: 0.5
Nodes (1): add prompt templates and video stage runs  Revision ID: 0004_add_prompt_templa

### Community 22 - "0005_add_voice_profiles.py / upgrade() / downgrade()"
Cohesion: 0.5
Nodes (1): add voice profiles  Revision ID: 0005_add_voice_profiles Revises: 0004_extend

### Community 23 - "0006_merge_runtime_heads.py / upgrade() / merge runtime migration heads  Revision ID: 0006_merge_runtime_heads Revises:"
Cohesion: 0.5
Nodes (1): merge runtime migration heads  Revision ID: 0006_merge_runtime_heads Revises:

### Community 24 - "当前职责 / README / 本地运行（使用项目根 venv）"
Cohesion: 0.5
Nodes (4): README, README, 当前职责, 本地运行（使用项目根 venv）

### Community 25 - "main.py / main()"
Cohesion: 1.0
Nodes (0): 

### Community 26 - "create_app() / __init__.py"
Cohesion: 1.0
Nodes (0): 

### Community 27 - "__init__.py / Developer-only Runtime helpers."
Cohesion: 1.0
Nodes (1): Developer-only Runtime helpers.

### Community 28 - "__init__.py"
Cohesion: 1.0
Nodes (0): 

### Community 29 - "__init__.py"
Cohesion: 1.0
Nodes (0): 

### Community 30 - "__init__.py"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "__init__.py"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "__init__.py"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "__init__.py"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "__init__.py"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "video_tasks.py"
Cohesion: 1.0
Nodes (0): 

### Community 36 - "__init__.py"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **11 isolated node(s):** `initial schema  Revision ID: 0001_initial_schema Revises: Create Date: 2026-`, `add imported videos  Revision ID: 0002_add_imported_videos Revises: 0001_init`, `add business modules  Revision ID: 0003_add_business_modules Revises: 0002_ad`, `add prompt templates and video stage runs  Revision ID: 0004_add_prompt_templa`, `add voice profiles  Revision ID: 0005_add_voice_profiles Revises: 0004_extend` (+6 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `main.py / main()`** (2 nodes): `main.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `create_app() / __init__.py`** (2 nodes): `__init__.py`, `create_app()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `__init__.py / Developer-only Runtime helpers.`** (2 nodes): `__init__.py`, `Developer-only Runtime helpers.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `__init__.py`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `__init__.py`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `__init__.py`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `__init__.py`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `__init__.py`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `__init__.py`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `__init__.py`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `video_tasks.py`** (1 nodes): `video_tasks.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `__init__.py`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_app()` connect `create_app() / UnavailableLicenseActivationAdapter / LicenseService` to `.get() / Base`, `HTTPException / Exception / AccountService`, `BaseModel / SettingsService / RenderService`, `StoryboardService / ScriptService / .require_project()`, `AICapabilityService / ai_capability_service.py / ProviderConnectivityError`, `VideoDeconstructionService / TaskManager / _StageDefinition`, `ProviderHTTPException / .generate_text() / AIJobRepository`, `ReviewService / utc_now() / DashboardService`, `WorkspaceService / workspace.py / TimelineRepository`, `VoiceService / _BuiltinVoiceProfile / .generate_track()`, `SubtitleService / _BuiltinSubtitleStyleTemplate / subtitles.py`, `AutomationService / AutomationRepository / ._to_task_dto()`, `PromptTemplateService / PromptTemplateRepository / ._to_stored()`, `SearchService / .search() / search.py`, `utc_now_iso() / BootstrapService / .runtime_selfcheck()`?**
  _High betweenness centrality (0.177) - this node is a cross-community bridge._
- **Why does `ok_response()` connect `ok_response() / assets.py / _svc()` to `.get() / Base`, `create_app() / UnavailableLicenseActivationAdapter / LicenseService`, `BaseModel / SettingsService / RenderService`, `StoryboardService / ScriptService / .require_project()`, `AICapabilityService / ai_capability_service.py / ProviderConnectivityError`, `VideoDeconstructionService / TaskManager / _StageDefinition`, `ReviewService / utc_now() / DashboardService`, `PromptTemplateService / PromptTemplateRepository / ._to_stored()`, `SearchService / .search() / search.py`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Why does `UnavailableLicenseActivationAdapter` connect `create_app() / UnavailableLicenseActivationAdapter / LicenseService` to `.get() / Base`, `HTTPException / Exception / AccountService`, `BaseModel / SettingsService / RenderService`, `StoryboardService / ScriptService / .require_project()`, `AICapabilityService / ai_capability_service.py / ProviderConnectivityError`, `VideoDeconstructionService / TaskManager / _StageDefinition`, `ProviderHTTPException / .generate_text() / AIJobRepository`, `ReviewService / utc_now() / DashboardService`, `WorkspaceService / workspace.py / TimelineRepository`, `VoiceService / _BuiltinVoiceProfile / .generate_track()`, `SubtitleService / _BuiltinSubtitleStyleTemplate / subtitles.py`, `AutomationService / AutomationRepository / ._to_task_dto()`, `PromptTemplateService / PromptTemplateRepository / ._to_stored()`, `SearchService / .search() / search.py`, `utc_now_iso() / BootstrapService / .runtime_selfcheck()`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Are the 173 inferred relationships involving `HTTPException` (e.g. with `get_license_service()` and `get_task()`) actually correct?**
  _`HTTPException` has 173 INFERRED edges - model-reasoned connections that need verification._
- **Are the 162 inferred relationships involving `ok_response()` (e.g. with `list_account_groups()` and `create_account_group()`) actually correct?**
  _`ok_response()` has 162 INFERRED edges - model-reasoned connections that need verification._
- **Are the 141 inferred relationships involving `Exception` (e.g. with `.generate()` and `.generate()`) actually correct?**
  _`Exception` has 141 INFERRED edges - model-reasoned connections that need verification._
- **Are the 53 inferred relationships involving `create_app()` (e.g. with `load_runtime_config()` and `create_runtime_engine()`) actually correct?**
  _`create_app()` has 53 INFERRED edges - model-reasoned connections that need verification._