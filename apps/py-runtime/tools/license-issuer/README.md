# 授权机工具

## 用途

用于在授权机上生成离线永续授权码，不用于客户机运行。

## 准备

1. 生成密钥对：

```powershell
venv\Scripts\python.exe apps/py-runtime/tools/license-issuer/generate_keypair.py --output-dir .runtime-data/licenses
```

2. 把公钥部署到客户机 Runtime 可读取的位置，并设置：

```powershell
$env:TK_OPS_LICENSE_PUBLIC_KEY_PATH="G:\path\to\license-public.pem"
```

3. 在授权机设置私钥路径：

```powershell
$env:TK_OPS_LICENSE_PRIVATE_KEY_PATH="G:\path\to\license-private.pem"
```

## 生成授权码

```powershell
venv\Scripts\python.exe apps/py-runtime/tools/license-issuer/issue_license.py --machine-code TKOPS-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
```

Windows 也可以直接双击：

```text
apps\py-runtime\tools\license-issuer\issue-license.bat
```
