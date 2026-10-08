[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$EvidencePath,

    [string]$RuntimeEvidencePath = "",

    [string]$ManifestPath = ""
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $PSCommandPath
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $scriptRoot "..\.."))
$validatorPath = Join-Path $repoRoot "scripts\p0-h-real-provider-evidence.mjs"

if (-not (Test-Path -LiteralPath $validatorPath -PathType Leaf)) {
    throw "P0-H 证据校验器不存在。"
}

$resolvedEvidencePath = [System.IO.Path]::GetFullPath($EvidencePath)
$resolvedRuntimeEvidencePath = ""
if ($RuntimeEvidencePath) {
    $resolvedRuntimeEvidencePath = [System.IO.Path]::GetFullPath($RuntimeEvidencePath)
    if (-not (Test-Path -LiteralPath $resolvedRuntimeEvidencePath -PathType Leaf)) {
        throw "Runtime evidence 文件不存在。"
    }
} elseif (-not (Test-Path -LiteralPath $resolvedEvidencePath -PathType Leaf)) {
    throw "待校验的 P0-H 人工证据不存在。"
}

if (-not $ManifestPath) {
    $version = (Get-Content -LiteralPath (Join-Path $repoRoot "package.json") -Raw -Encoding UTF8 |
        ConvertFrom-Json).version
    if (-not $RuntimeEvidencePath) {
        $evidence = Get-Content -LiteralPath $resolvedEvidencePath -Raw -Encoding UTF8 |
            ConvertFrom-Json
        if ($evidence.appVersion) {
            $version = [string]$evidence.appVersion
        }
    }
    $ManifestPath = Join-Path $repoRoot "dist\releases\$version\windows-x86_64\release-manifest.json"
}

$resolvedManifestPath = [System.IO.Path]::GetFullPath($ManifestPath)
if (-not (Test-Path -LiteralPath $resolvedManifestPath -PathType Leaf)) {
    throw "当前制品的 Release Manifest 不存在。"
}

$node = Get-Command node -ErrorAction Stop
if ($resolvedRuntimeEvidencePath) {
    & $node.Source $validatorPath `
        --runtime-evidence $resolvedRuntimeEvidencePath `
        --manifest $resolvedManifestPath `
        --output $resolvedEvidencePath
} else {
    & $node.Source $validatorPath `
        --evidence $resolvedEvidencePath `
        --manifest $resolvedManifestPath
}

if ($LASTEXITCODE -ne 0) {
    throw "P0-H 人工真实 Provider 证据未通过校验。"
}
