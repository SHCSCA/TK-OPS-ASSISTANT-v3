# 2026-05-26 真实渲染最小闭环设计规格

## 1. 对应计划

对应计划：`docs/superpowers/plans/2026-05-25-delivery-readiness.md`

本规格覆盖阶段 4 的第一批切片：渲染与导出中心的 Runtime 最小真实输出链路。

## 2. 目标

用户在渲染与导出中心创建渲染任务后，Runtime 必须能生成一个可验证的本地输出文件，而不是只创建数据库任务或识别测试预置文件。

最小闭环要求：

- `POST /api/renders/tasks` 创建任务后触发受控的最小渲染执行。
- 输出文件落到统一 Runtime 数据目录下的 `exports` 子目录。
- 成功任务必须写入 `output_path`、`progress=100`、`status=completed`、`started_at`、`finished_at`。
- 缺少 FFmpeg 或执行失败时，任务必须转为 `failed`，并暴露中文错误、错误码和可重试动作。
- 任务详情必须继续通过统一信封返回 `stage`、`output`、`failure`，前端可以直接展示。
- 取消和重试语义保持可追踪：可取消任务返回取消结果，不可重试任务返回结构化冲突。

## 3. 边界

本切片只做最小真实渲染闭环，不扩展产品范围：

- 不实现完整时间线合成器。
- 不实现多轨音视频混流、字幕烧录和 GPU 加速。
- 不改 16 页产品范围和路由树。
- 不触碰旧 `desktop_app/`。
- 不把发布、自动化、账号或浏览器执行链路纳入本阶段。

## 4. 后端设计

### 4.1 RenderService 职责

`RenderService.create_task()` 仍是任务入口，但保存任务后必须立即调用最小渲染执行器。

执行流程：

1. 创建 `RenderTask`，状态为 `queued`。
2. 将任务更新为 `rendering`，记录 `started_at`，广播状态。
3. 通过配置总线派生的 Runtime 数据目录生成输出路径。
4. 调用 FFmpeg runner 生成一个短时长竖屏 MP4 文件。
5. 成功后校验输出文件存在且大小大于 0。
6. 更新任务为 `completed`，写入 `output_path`、`progress=100`、`finished_at`。
7. 任一步失败时记录日志，任务更新为 `failed`，写入中文 `error_message` 和错误码。

最小输入约束：

- `project_id` 和 `project_name` 继续保留在任务记录中。
- 若暂未形成完整 `Timeline/Asset` 渲染输入，输出文件仍必须按项目上下文命名并落在 Runtime export 目录，避免伪造业务结果。
- 后续完整时间线合成必须沿用当前执行器边界扩展，不在页面内拼业务规则。

### 4.2 FFmpeg runner

新增独立媒体执行模块，避免把命令拼接堆入 `render_service.py`。

建议文件：

- `apps/py-runtime/src/media/ffmpeg.py`
- `apps/py-runtime/src/media/__init__.py`

职责：

- 解析 FFmpeg 可执行文件。
- 生成最小黑色视频 MP4。
- 捕获 `FileNotFoundError`、超时、非零退出码和未知异常。
- 返回结构化结果，包含输出路径、错误码、中文错误信息。

FFmpeg 解析优先级：

1. 配置总线写入的 FFmpeg 路径。
2. 环境变量 `TK_OPS_FFMPEG_PATH`。
3. Tauri resource 目录中的内置 FFmpeg。
4. 系统 `PATH`。

缺失时错误码为 `media.ffmpeg_unavailable`，中文提示为“FFmpeg 未安装或未配置到可执行路径。”。

### 4.3 配置与目录

所有路径必须来自统一配置入口：

- `RuntimeConfig.data_dir` 作为默认数据根。
- 输出目录为 `RuntimeConfig.data_dir / "exports"`。
- 不允许页面、测试或服务各自硬编码另一套导出目录。

`RenderService` 构造函数可接收 `runtime_config` 或精简的 `export_root`，测试中可注入临时目录。

### 4.4 错误与日志

所有异常必须捕获并记录：

- 服务层使用 `log.exception(...)` 记录不可预期异常。
- FFmpeg 可预期失败使用结构化错误返回，避免把 traceback 暴露给用户。
- API 错误继续走统一错误信封。

任务失败 DTO：

- `failure.error_code` 优先使用任务持久化错误码。
- `failure.error_message` 使用中文可展示文案。
- `failure.retryable` 对 FFmpeg 缺失、执行失败、输出缺失保持 `true`。
- `failure.next_action.key` 使用 `retry-render` 或 `verify-output`。

## 5. 数据模型

`RenderTask` 至少补齐：

- `error_code: str | None`

迁移与兼容：

- SQLAlchemy 模型新增字段。
- Alembic 新增迁移。
- `persistence.engine._repair_legacy_render_task_schema()` 补 legacy schema repair。
- 旧任务没有错误码时，失败 DTO 回落到 `render.task_failed`。

暂不新增复杂输入字段，避免在时间线合成未完成前制造半成品契约。

## 6. API 契约

保持现有 API：

- `POST /api/renders/tasks`
- `GET /api/renders/tasks/{task_id}`
- `POST /api/renders/tasks/{task_id}/cancel`
- `POST /api/renders/tasks/{task_id}/retry`

创建任务成功响应示例：

```json
{
  "ok": true,
  "data": {
    "status": "completed",
    "progress": 100,
    "output": {
      "exists": true,
      "size_bytes": 12345,
      "can_open": true
    },
    "failure": {
      "error_code": null,
      "retryable": false
    }
  }
}
```

FFmpeg 缺失响应仍为 201 创建成功，但任务状态为 `failed`：

```json
{
  "ok": true,
  "data": {
    "status": "failed",
    "failure": {
      "error_code": "media.ffmpeg_unavailable",
      "error_message": "FFmpeg 未安装或未配置到可执行路径。",
      "retryable": true
    }
  }
}
```

不可重试任务继续返回：

```json
{
  "ok": false,
  "error": "只有失败或已取消的任务可以重试。",
  "error_code": "render.task_not_retryable"
}
```

## 7. 测试规格

必须先写失败测试，再实现生产代码。

Runtime 单元测试：

- `tests/runtime/test_render_service.py`
  - `test_create_task_runs_minimal_renderer_and_writes_output_file`
  - `test_create_task_records_structured_failure_when_renderer_unavailable`
  - `test_retry_task_clears_error_code`
  - `test_cancel_task_returns_cancelled_result_for_rendering_task`

API 契约测试：

- `tests/contracts/test_renders_runtime_contract.py`
  - `test_create_render_task_contract_writes_real_output_file`
  - `test_retry_non_retryable_render_returns_structured_conflict`
  - `test_cancel_running_render_contract_returns_cancelled_envelope`

迁移测试：

- `tests/runtime/test_render_schema_migration.py`
  - legacy `render_tasks` repair 后包含 `error_code`。

验证命令：

```powershell
python -m pytest tests/runtime/test_render_service.py tests/contracts/test_renders_runtime_contract.py tests/runtime/test_render_schema_migration.py
python -m pytest tests/contracts/test_bootstrap_contract.py tests/runtime/test_bootstrap_routes.py
```

若本地没有 FFmpeg，真实执行测试应通过可注入 runner 验证服务逻辑，另保留 FFmpeg 缺失路径测试，不能伪称本机真实 FFmpeg 已验证。

## 8. 子代理分工

- `.codex/agents/agents-orchestrator.toml`：编排阶段 4 开发-QA 循环和质量门禁。
- `.codex/agents/engineering-backend-architect.toml`：审核后端服务边界、错误码、配置总线与数据模型。
- `.codex/agents/testing-api-tester.toml`：审核 Runtime API 契约和输出文件证明。
- `.codex/agents/engineering-code-reviewer.toml`：最终代码审查，关注正确性、可维护性和异常日志。

主代理负责规格落地、关键实现方向、最终验证与风险报告。

## 9. 验收标准

- 创建渲染任务后，服务层能产出一个存在且非空的本地 MP4 文件。
- FFmpeg 不可用时用户可见中文失败原因，日志可追踪，任务可重试。
- 输出路径、失败错误码、任务状态都可通过 API 查询。
- 取消和重试行为有契约测试覆盖。
- 没有新增超大文件，没有把命令逻辑塞到页面或旧壳。
