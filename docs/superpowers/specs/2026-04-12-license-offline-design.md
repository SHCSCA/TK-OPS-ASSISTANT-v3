# 离线永久授权与独立前置启动流程设计

## 目标

为 TK-OPS 提供真实可用的离线一机一码授权链路，并把应用启动体验重构为独立的前置流程：

- 启动后先进入独立前置加载窗口
- 前置流程负责 Runtime 检查、授权检查、授权录入、系统初始化
- 只有在授权完成且初始化完成后，才进入主工作台

本轮不做联网授权、试用、续期、撤销和多设备迁移。

## 范围

- Runtime 机器码生成
- Runtime 离线授权码验签
- 授权状态持久化
- 授权机 BAT 与签发脚本
- 桌面端独立前置启动流程
- 授权页与初始化页拆分
- 主工作台延后挂载

## 非目标

- 不做原生多窗口管理
- 不做联网授权服务
- 不做授权撤销
- 不做发布版安装器

## 授权模型

### 机器码

Runtime 在 Windows 上读取以下信息并归一化：

- `MachineGuid`
- `Win32_ComputerSystemProduct.UUID`
- 系统盘卷序列号

归一化后做 `SHA-256`，再转为用户可读分组码，作为公开机器码展示给用户。

### 授权码

授权码采用 `Ed25519` 非对称签名，格式固定为：

- `base64url(payload_json).base64url(signature_bytes)`

`payload_json` 固定字段：

- `machineCode`
- `licenseType`
- `issuedAt`
- `version`

客户端只持有公钥。授权机持有私钥。

### 激活规则

`POST /api/license/activate` 的校验顺序：

1. 检查授权码格式
2. 解包 payload
3. 校验签名
4. 校验 `machineCode` 与本机一致
5. 校验 `licenseType === "perpetual"`
6. 写入本地授权记录

## Runtime 设计

### 接口

`GET /api/license/status`

返回：

- `active`
- `restrictedMode`
- `machineCode`
- `machineBound`
- `licenseType`
- `maskedCode`
- `activatedAt`

`POST /api/license/activate`

输入：

- `activationCode`

输出与 `status` 相同。

### 存储

`license_grant` 保持单记录，字段为：

- `active`
- `restricted_mode`
- `machine_code`
- `machine_bound`
- `license_type`
- `signed_payload`
- `masked_code`
- `activated_at`

### 错误与日志

授权失败必须统一返回中文错误：

- 授权码格式非法
- 授权码签名校验失败
- 授权码与当前机器不匹配
- 未配置授权公钥
- 授权数据损坏

所有授权相关日志继续写入 `audit` 分类，并带 `requestId`。

## 桌面端设计

### 总体结构

桌面端启动不再直接进入主壳。

新的根流程：

1. `BootstrapGate`
2. `BootstrapLoadingScreen`
3. `LicenseActivationScreen`
4. `BootstrapInitializationScreen`
5. `AppShell`

只有 `BootstrapGate` 判定“授权完成且初始化完成”后，才渲染 `AppShell`。

### 状态机

独立前置流程状态固定为：

- `boot_loading`
- `boot_error`
- `license_required`
- `initialization_required`
- `ready`

其中：

- Runtime 或配置读取失败时进入 `boot_error`
- 授权未完成时进入 `license_required`
- 授权已完成但初始化未完成时进入 `initialization_required`
- 授权与初始化都完成后进入 `ready`

### 页面拆分

#### 1. 启动加载页

职责：

- 展示启动进度
- 展示 Runtime、配置、授权检查状态
- 失败时提供重试按钮

要求：

- 全屏独立界面
- 不显示 Sidebar、Detail Panel、主状态栏

#### 2. 授权页

职责：

- 说明当前需要永久授权
- 展示机器码
- 提供复制机器码按钮
- 提供授权码输入框
- 完成授权后进入初始化页

#### 3. 初始化页

职责：

- 配置工作区、缓存、导出、日志目录
- 配置基础 AI 默认项
- 保存初始化配置
- 完成后进入主工作台

要求：

- 授权成功前不能进入初始化页

### 主工作台进入条件

同时满足以下条件才进入主工作台：

- `licenseStore.active === true`
- `configBusStore.settings !== null`
- 独立前置流程显式标记初始化已完成

初始化完成标记不再依赖“配置已读取”，而是依赖一次真实的初始化确认。

## 授权机工具

目录：

- `apps/py-runtime/tools/license-issuer/issue-license.bat`
- `apps/py-runtime/tools/license-issuer/issue_license.py`
- `apps/py-runtime/tools/license-issuer/generate_keypair.py`
- `apps/py-runtime/tools/license-issuer/README.md`

要求：

- 私钥不进入仓库
- 私钥不进入客户机
- BAT 面向 Windows 授权人员直接使用

## UI 约束

- 不允许先出现主工作台壳层再阻塞
- 不允许用户看到空白页等待
- 所有用户可见文案统一中文
- 授权输入区必须在首屏可见
- 机器码、授权码输入、下一步操作必须一眼可见

## 测试要求

### Runtime

- 未授权状态返回真实机器码
- 正确授权码可激活并持久化
- 错误签名、错误机器码、损坏授权码返回统一中文错误

### Desktop

- 启动时先显示独立前置加载页
- Runtime 异常时显示阻塞错误态
- 未授权时显示授权页而不是主壳
- 授权成功后进入初始化页
- 初始化完成后才进入 Dashboard

### 工具

- 密钥生成成功
- 签发成功
- 非法机器码与缺失私钥报错明确
