$ErrorActionPreference = "Stop"

try {
    $prototypeRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location -LiteralPath $prototypeRoot

    if (-not (Test-Path -LiteralPath "node_modules")) {
        Write-Host "首次启动，正在安装原型依赖……"
        npm install
    }

    Write-Host "TK-OPS 原型即将在 http://127.0.0.1:4173/ 启动。"
    npm run dev -- --host 127.0.0.1 --port 4173 --strictPort
}
catch {
    Write-Error "原型启动失败：$($_.Exception.Message)"
    exit 1
}
