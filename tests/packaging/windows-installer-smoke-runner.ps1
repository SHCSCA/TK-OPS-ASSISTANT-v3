param(
    [Parameter(Mandatory = $true)]
    [string]$ScriptPath,
    [Parameter(Mandatory = $true)]
    [string]$InstallerPath
)

$ErrorActionPreference = "Stop"
$utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
$source = Get-Content -LiteralPath $ScriptPath -Raw -Encoding UTF8
$script = [ScriptBlock]::Create($source)
& $script -InstallerPath $InstallerPath
