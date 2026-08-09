# TK-OPS 版本管理规范

> 生效日期：2026-08-02  
> 当前目标版本：`0.4.11`  
> 适用范围：Desktop、Tauri、Python Runtime、Windows 安装包与免安装包

## 1. 版本格式

项目统一采用语义化版本：

```text
MAJOR.MINOR.PATCH
主版本.次版本.补丁版本
```

版本升级按本次交付中影响最高的变更决定，不按提交数量或文件数量决定。

## 2. 升级规则

### PATCH：补丁版本

以下兼容性变更升级最后一位，例如 `0.4.7 -> 0.4.8`：

- 修复 UI、Runtime、打包、许可证、执行环境或数据展示缺陷。
- 修复安全、稳定性、性能或错误处理问题，但不改变公开使用方式。
- 一个交付批次可包含一个或多个相关缺陷，只升级一次补丁号。
- 已向用户发出的测试包如果修复代码后再次发包，必须再次升级补丁号；仅对相同代码重新构建时允许保留版本，并以 build ID 和 SHA-256 区分。

### MINOR：次版本

以下向后兼容的新能力升级中间一位，并将补丁位归零，例如 `0.4.8 -> 0.5.0`：

- 新增正式页面、完整业务链路或用户可感知的核心能力。
- 新增向后兼容的 Runtime API、Provider 能力或持久化模型。
- 对现有流程进行较大扩展，但旧数据和旧调用仍可继续使用。
- 同一版本同时包含新功能和缺陷修复时，按次版本发布。

### MAJOR：主版本

以下不兼容变更升级第一位，并将其余位归零，例如 `0.9.0 -> 1.0.0`：

- 产品主线、账号隔离边界或核心数据主链发生不兼容变化。
- Runtime API、数据库、许可证、执行协议或配置格式无法向后兼容。
- 旧版本无法原位升级，或必须执行明确的数据迁移与回退方案。
- 产品达到对外稳定承诺并完成 `1.0.0` 发布门禁。

## 3. 不跟随应用版本的编号

以下编号有独立生命周期，不得与应用版本混用：

- Runtime HTTP API 使用 `/api/v1` 等接口版本。
- Alembic 使用迁移 revision。
- 定位、Prompt、模板等业务对象使用各自的不可变版本号。
- Runtime manifest 使用 `formatVersion`、`lifecycleProtocol` 和 Schema 读写范围。

应用版本变化不代表这些编号必须变化；只有对应契约变化时才单独升级。

## 4. 单一真源与同步范围

正式版本唯一真源为根目录 `package.json` 的 `version`。

执行 `npm run version:sync` 后，必须同步到：

- `apps/desktop/src-tauri/Cargo.toml`
- `apps/desktop/src-tauri/Cargo.lock` 中 `tk-ops-desktop` 包版本
- `apps/desktop/src-tauri/tauri.conf.json`
- `apps/py-runtime/pyproject.toml`

以下文件属于构建产物，不允许为了“看起来一致”而手工改版本：

- `apps/desktop/src-tauri/resources/runtime/tk-ops-runtime.manifest.json`
- `dist/releases/<version>/windows-x86_64/release-manifest.json`
- 安装包和免安装包文件名

它们必须由 Runtime sidecar 和 Windows release 构建脚本基于版本真源重新生成，同时更新二进制哈希、build ID 和时间戳。

## 5. 每次交付流程

1. 根据本规范确定本次版本级别，以影响最高的变更为准。
2. 修改根 `package.json` 的版本号，并执行 `npm run version:sync`。
3. 在 `CHANGELOG.md` 的 `Unreleased` 中记录真实完成的变更，不提前宣称尚未完成的功能。
4. 执行 `npm run version:check`，禁止 Desktop、Tauri 和 Runtime 源版本不一致。
5. 完成对应测试、类型检查、Runtime 契约检查和主链路回归。
6. 运行 Windows release 构建；构建脚本重新生成 Runtime manifest、安装包、免安装包、release manifest 和 SHA-256。
7. 对外提供制品时同时给出版本、发布通道、build ID 和 SHA-256。

## 6. 发布门禁

- 版本号未更新：禁止交付包含代码变化的新 EXE。
- 版本镜像不一致：禁止构建正式制品。
- Runtime manifest 与二进制版本或哈希不一致：禁止打包。
- Changelog 未记录真实变更：禁止正式发布。
- 测试失败、E2E 未完成或制品 smoke 未通过：只能保留为失败证据，不得标记为可测试候选。
- 禁止复用旧版本号覆盖已经对外发送的不同代码制品。

## 7. 本次版本判定

本次范围是：

- 修复未保存弹窗三个按钮无效。
- 修复定位版本内容不可读、不能查看详情、不能基于版本修改。
- 增加相关错误状态、接口契约和回归测试。

这些变化保持现有账号定位主链和 API 主版本兼容，因此从 `0.4.7` 升级为 `0.4.8`。

## 8. 0.4.9 版本判定

`0.4.8` 测试包已对外提供，但免安装 ZIP 根目录同时暴露 Desktop 与 Runtime 两个 EXE。此次只修正 Windows 制品布局与 Runtime 启动路径，不改变产品主链、Runtime HTTP API 或数据格式，因此按补丁版本升级为 `0.4.9`。

## 9. 0.4.10 与 0.4.11 版本判定

`0.4.10` 完成机器身份、许可证、执行环境恢复、监督登录取消和 Release Manifest v2 加固，并已作为测试候选接受外部验收。验收后补齐两条独立异常 E2E、登录准备阶段的后端可取消边界、取消后的可恢复界面，以及免安装 ZIP 全新解压冷启动门禁。上述变更保持 Runtime HTTP API 与数据格式兼容，但会生成不同 Desktop、Runtime 和 portable 制品，因此按补丁版本升级为 `0.4.11`，不得覆盖既有 `0.4.10` 制品。
