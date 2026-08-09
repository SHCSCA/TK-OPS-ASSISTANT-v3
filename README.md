# TK-OPS

TK-OPS 是面向 TikTok 内容创作者的本地优先 Windows 桌面应用，产品定位是“账号定位驱动的 AI 短视频策划、批量生产与媒体工作台”，不是团队后台、经营系统或手动多轨剪辑器。

已批准的 P0 账号基础与桌面交付计划已于 2026-08-01 完成：

- P0-A 数据库安全基线已于 2026-07-26 通过阶段验收，覆盖统一数据库配置、旧库指纹、迁移锁、备份恢复、Alembic `0015–0017` 和启动前目标契约校验。
- P0-B Runtime v1 内核已于 2026-07-26 通过阶段验收，`/api/v1`、统一错误与日志、持久任务、账号事件、重放和 legacy 薄转发已成为生产底座。
- P0-C 账号纵向链已于 2026-07-26 通过阶段验收，五状态账号、真实连接、定位知识品牌对象、账号任务与全层隔离已成为 Runtime v1 正式契约。
- P0-D Desktop 账号上下文已于 2026-07-26 通过阶段验收，真实授权、双账号隔离、账号页面记忆、归档清理和两档 PC 窗口链路均已验证。
- P0-E 系统 AI 配置纵向链已于 2026-07-26 通过阶段验收，Provider、模型、能力、路由、Prompt、合成模板和账号 Recipe 均通过统一 v1 契约管理。
- P0-F 已完成正式十三 Route、十个账号级入口、旧 URL 单次重定向、Runtime sidecar、Tauri Supervisor、动态端口、生产数据目录、单实例、退出清理和 Windows NSIS 安装包验收。
- 旧 `Project / Timeline` 代码只保留为后续迁移参考，已不再进入正式导航和业务路由；P1 / P2 尚未开始，必须另行批准计划与规格。

目标主链固定为：

```text
Account
→ ContentPlan
→ ContentItem
→ Script
→ Storyboard
→ ProductionBatch
→ ContentVariant
→ CompositionSpec
→ RenderTask
→ PublishTask
```

## 版本真源

- 唯一可编辑版本：根 `package.json` 的 `version`
- 镜像版本由脚本维护：
  - `apps/desktop/src-tauri/Cargo.toml`
  - `apps/desktop/src-tauri/tauri.conf.json`
  - `apps/py-runtime/pyproject.toml`
- 命令：
  - `npm run version:sync`
  - `npm run version:check`
- 发布记录：`CHANGELOG.md`

## 开发环境初始化（Windows）

1. 安装 Node.js、Rust（含 `cargo`）、Python
2. 安装前端依赖：`npm --prefix apps/desktop install`
3. 创建虚拟环境：`python -m venv venv`
4. 安装 Runtime 依赖：`venv\\Scripts\\python.exe -m pip install -e "./apps/py-runtime[dev]"`

## 开发态一键启动桌面应用

- 主入口：`npm run app:dev`
- Windows 双击入口：`start-desktop-dev.cmd`

启动器行为：

- Tauri Supervisor 校验并启动已打包 Runtime sidecar，不回退系统 Python
- Runtime 每次启动只监听动态分配的 `127.0.0.1` 端口
- Desktop 通过 Tauri command 获取本次连接与内存会话，不持久化端口或令牌
- Runtime 就绪后进入真实 Bootstrap；关闭桌面应用后优雅回收整个进程树
- 如需仅运行浏览器前端，使用 `npm run desktop:dev`，Vite 默认监听 `127.0.0.1:1420`

## 常用命令

- 仅启动 Runtime：`npm run runtime:dev`
- 仅启动 Tauri 开发态：`npm run desktop:tauri:dev`
- Desktop 测试：`npm --prefix apps/desktop run test`
- Desktop 类型检查：`npm run typecheck`
- Desktop 构建：`npm --prefix apps/desktop run build`
- Runtime 测试：`venv\\Scripts\\python.exe -m pytest tests/runtime -q`
- Contract 测试：`venv\\Scripts\\python.exe -m pytest tests/contracts -q`
- 浏览器 E2E：`npm run test:e2e`
- 准备 Runtime sidecar：`npm run runtime:sidecar:prepare`
- Sidecar smoke：`npm run test:sidecar-smoke`
- 构建 NSIS：`npm run desktop:tauri -- build --bundles nsis`
- 安装包 smoke：`npm run test:installer-smoke`

## 离线授权工具

- 客户机启动后会显示启动加载层和首启授权向导
- 向导会展示本机机器码，用户可复制后发给授权人员
- 授权机工具目录：`apps/py-runtime/tools/license-issuer`
- 生成密钥对：
  - `venv\\Scripts\\python.exe apps/py-runtime/tools/license-issuer/generate_keypair.py --output-dir .runtime-data/licenses`
- 签发授权码：
  - `venv\\Scripts\\python.exe apps/py-runtime/tools/license-issuer/issue_license.py --machine-code <机器码>`
- Windows 授权机也可直接双击：
  - `apps\\py-runtime\\tools\\license-issuer\\issue-license.bat`

## 历史视觉参考

- 旧 Stitch、Graphify、M05–M15 和交互原型只作为迁移或视觉参考，不是当前默认设计流程，也不得覆盖现行 PRD、UI、架构与 P0 规格。
- 当前交互原型位于 `docs/prototypes/`；生产实现必须回到 Vue、Pinia、Runtime 适配层与 CSS token 架构，并使用真实数据或中性空态。

## 当前边界

- 许可证激活已改为本地离线签名校验，不接入远端授权服务
- 账号是工作区与数据隔离边界；定位、知识、内容、任务、文件、日志和 AI 配方必须随账号切换
- 正常工作区目标为十个账号级入口，账号管理和 AI 与系统设置属于系统级页面
- 自动合成只通过受控 `CompositionSpec` 表达，不提供 AI 剪辑工作台或手动多轨时间线
- 旧 `Project / Timeline`、独立配音、字幕、渲染和自动化入口只作为迁移参考，不得继续扩展为新产品能力
- 当前实施状态以 `docs/PROJECT-STATUS.md` 为准
- `docs/RUNTIME-API-CALLS.md` 是冻结的 legacy 接口索引；新增 `/api/v1` 契约只维护在 `docs/api/v1/`
- 当前 P0 交付状态和真实验收证据以 `docs/PROJECT-STATUS.md` 为准
