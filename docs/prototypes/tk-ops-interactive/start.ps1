param(
  [int]$Port = 4173
)

$ErrorActionPreference = "Stop"
$prototypeRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $prototypeRoot "..\..\..")).Path
$prototypeUrl = "http://127.0.0.1:$Port/docs/prototypes/tk-ops-interactive/"

try {
  Write-Host "TK-OPS 本地交互原型：$prototypeUrl"
  python -m http.server $Port --bind 127.0.0.1 --directory $repositoryRoot
} catch {
  Write-Error "本地原型启动失败：$($_.Exception.Message)"
  exit 1
}
