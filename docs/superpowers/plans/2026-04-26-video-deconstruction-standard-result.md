# Video Deconstruction Standard Result Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将视频拆解结果统一为脚本文案、视频关键帧、内容结构三大板块，避免前端从旧字段和临时 JSON 中猜测展示数据。

**Architecture:** Runtime 负责把多模态模型输出归一化为标准 DTO，同时保留旧 transcript / segments / structure 字段兼容既有调用。前端 store 拉取统一结果，页面三栏只消费标准字段，不再直接解析 `metadataJson`、`scriptJson` 作为主展示来源。

**Tech Stack:** FastAPI、Pydantic、SQLAlchemy Repository、Vue 3、Pinia、TypeScript、Vitest、Pytest。

---

## 文件地图

- 修改 `apps/py-runtime/src/schemas/video_deconstruction.py`：新增标准结果 DTO。
- 新增 `apps/py-runtime/src/services/video_deconstruction_result_builder.py`：集中归一化脚本文案、关键帧、内容结构和来源信息。
- 修改 `apps/py-runtime/src/services/video_multimodal_analysis_service.py`：提示词要求模型输出标准三栏 JSON。
- 修改 `apps/py-runtime/src/services/video_deconstruction_service.py`：一键拆解和查询结果返回标准结构。
- 修改 `apps/py-runtime/src/api/routes/video_deconstruction.py`：新增 `GET /videos/{video_id}/result`。
- 修改 `apps/desktop/src/types/runtime.ts`：同步标准 DTO 类型。
- 修改 `apps/desktop/src/app/runtime-client.ts`：新增 `fetchVideoResult`。
- 修改 `apps/desktop/src/stores/video-import.ts`：以统一结果作为状态来源。
- 修改 `apps/desktop/src/pages/video/VideoDeconstructionCenterPage.vue`：三栏读取标准结构。
- 修改 `tests/runtime/test_video_deconstruction_runtime_api.py`、`tests/contracts/test_video_deconstruction_api.py`、`apps/desktop/tests/video-deconstruction.spec.ts`：补齐契约与展示回归。

## 实施步骤

- [ ] **Step 1: 写后端失败测试**
  - 在 Runtime API 测试中断言一键拆解响应包含 `script`、`keyframes`、`contentStructure`、`source`。
  - 在契约测试中断言新增 `GET /videos/{video_id}/result` 返回相同标准结构。

- [ ] **Step 2: 写前端失败测试**
  - 在视频拆解页面测试中 mock 标准结果，断言脚本文案、视频关键帧、内容结构三栏直接展示标准字段。

- [ ] **Step 3: 实现后端 DTO 与归一化服务**
  - 新增标准 DTO。
  - 新增结果构建服务，负责解析多模态 artifact、旧 transcript / segments / structure，并输出统一结构。

- [ ] **Step 4: 调整模型提示词与 Runtime 接口**
  - 多模态视频提示词改为输出标准 JSON。
  - 一键拆解结果和查询结果都返回标准结构。

- [ ] **Step 5: 调整前端状态与三栏展示**
  - store 新增 `results` 缓存。
  - 页面三栏优先使用标准结构，旧结构仅作为兼容兜底。

- [ ] **Step 6: 验证**
  - 运行 Runtime 相关测试。
  - 运行视频拆解与 AI 设置前端测试。
  - 运行前端构建。

## 边界

- 不新增第四个展示板块。
- 不移除旧字段，避免破坏已有接口调用。
- 不把分镜生成逻辑塞入视频拆解页；视频拆解只输出可回流结构。
- 不在前端解析 Provider 原始输出，所有 Provider 差异必须在 Runtime 归一化。
