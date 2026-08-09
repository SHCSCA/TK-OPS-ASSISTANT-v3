# 授权机工具

## 用途

用于在授权机上生成离线永续授权码，不用于客户机运行。

## 准备

### 首次初始化

密钥对只能生成一次。私钥用于签发许可证，必须离线备份且不得进入安装包；公钥必须在构建前部署到 Runtime 资源目录。

1. 仅在不存在密钥对时生成：

```powershell
venv\Scripts\python.exe apps/py-runtime/tools/license-issuer/generate_keypair.py --output-dir .runtime-data/licenses
```

脚本发现任一密钥文件已经存在时会拒绝覆盖，防止误操作导致已发布 Runtime 与签发私钥失配。

2. 构建正式 Runtime 前，部署匹配的公钥：

```powershell
Copy-Item .runtime-data\licenses\license-public.pem apps\py-runtime\resources\license-public.pem
```

3. 在授权机设置私钥路径；默认路径已经是 `.runtime-data\licenses\license-private.pem`：

```powershell
$env:TK_OPS_LICENSE_PRIVATE_KEY_PATH="G:\secure\license-private.pem"
```

签发工具会在生成授权码前校验私钥与 Runtime 公钥是否匹配。不匹配时会直接失败，不会生成无法使用的授权码。

## 生成授权码

从客户机激活页复制完整机器码，然后执行：

```powershell
venv\Scripts\python.exe apps/py-runtime/tools/license-issuer/issue_license.py --machine-code TKOPS-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
```

Windows 也可以直接双击：

```text
apps\py-runtime\tools\license-issuer\issue-license.bat
```

交互模式会自动把授权码复制到剪贴板。把这段授权码粘贴到客户机的“许可证密钥”输入框即可。

## 重要边界

- 不要为每台客户机重新生成密钥对；每台客户机只需要使用自己的机器码签发新授权码。
- 不要把 `license-private.pem` 放入 Runtime、免安装包、源码提交或客户机。
- 更换签发密钥等同许可证体系轮换，旧 Runtime 与旧许可证不会自动兼容，必须单独制定迁移方案。
