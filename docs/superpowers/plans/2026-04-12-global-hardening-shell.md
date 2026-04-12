# 第 0 步全局硬化与壳层重做实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 TK-OPS 当前桌面应用硬化为中文、稳定、现代化的启动与主壳层基线。

**Architecture:** 保留 Tauri + Vue + Pinia + Runtime HTTP 架构，不新增业务域模型。本轮只重做全局壳层、创作总览和首启前置页，并修复全局可见乱码与授权工具文案。

**Tech Stack:** Vue 3、TypeScript、Pinia、Vue Router、CSS Variables、FastAPI Runtime、Stitch CLI 设计参考。

---

## 边界

- 不实现脚本、分镜、媒体、渲染、发布的新业务能力。
- 不恢复 `plugins/superpowers` 删除项。
- 不在仓库根恢复 `node_modules`。
- Stitch CLI 只作为视觉参考，最终代码遵守当前项目结构。

## 任务

1. 文档同步：补充第 0 步 plan/spec，明确视觉、文案、测试和范围。
2. 全局中文修复：路由、壳层、首页、首启页、授权工具、Runtime 授权错误统一中文。
3. 壳层重做：Title Bar、Sidebar、Detail Panel、Status Bar 现代化，移除开发路径显示。
4. 首页重做：以创作任务指挥台为主视觉，保留真实项目创建/打开链路。
5. 首启前置页重做：加载、授权、初始化三个状态视觉统一。
6. 最终验证：只在全部完成后执行完整前端、Runtime、契约和一键启动验证。
