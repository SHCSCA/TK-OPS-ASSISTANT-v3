# Python Runtime Creative Chain Baseline

`apps/py-runtime` 是 TK-OPS 的本地 Runtime，技术栈主线为 `Python + FastAPI + SQLite`。

## 当前职责

- 提供 FastAPI 应用工厂与启动入口
- 提供统一服务层：设置、许可证、项目、AI 能力、脚本、分镜
- 使用 SQLite 持久化系统配置、许可证、项目上下文、AI 配置、AI 作业、脚本版本、分镜版本
- 输出结构化日志并统一错误信封（含 `requestId`）
- 提供离线一机一码授权：机器码生成、授权码验签、授权状态持久化

## 本地运行（使用项目根 venv）

1. 在仓库根创建虚拟环境：`python -m venv venv`
2. 安装依赖：`venv\\Scripts\\python.exe -m pip install -e "./apps/py-runtime[dev]"`
3. 启动 Runtime：`npm run runtime:dev`

也可直接使用：
`venv\\Scripts\\python.exe -m uvicorn main:app --app-dir apps/py-runtime/src --host 127.0.0.1 --port 8000 --reload`

## 测试

- Runtime 测试：`venv\\Scripts\\python.exe -m pytest tests/runtime -q`
- Contract 测试：`venv\\Scripts\\python.exe -m pytest tests/contracts -q`

## 目录说明

- `src/api/routes/`：`/api/dashboard`、`/api/settings`、`/api/license`、`/api/scripts`、`/api/storyboards`
- `src/app/`：应用启动、配置、日志、异常处理
- `src/services/`：业务编排服务
- `src/repositories/`：SQLite 数据访问封装
- `src/persistence/`：数据库初始化与迁移
- `src/schemas/`：请求/响应 DTO 与信封定义
- `tools/license-issuer/`：离线授权机工具、密钥生成脚本、BAT 入口

## 离线授权

- Runtime 只持有公钥，用于校验授权码
- 授权机持有私钥，用于生成授权码
- 公钥路径默认读取 `TK_OPS_LICENSE_PUBLIC_KEY_PATH`，未配置时回退到仓库受控路径
- 可使用以下脚本生成密钥对：

```powershell
venv\Scripts\python.exe apps/py-runtime/tools/license-issuer/generate_keypair.py --output-dir .runtime-data/licenses
```

- 授权机签发授权码：

```powershell
venv\Scripts\python.exe apps/py-runtime/tools/license-issuer/issue_license.py --machine-code TKOPS-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
```
