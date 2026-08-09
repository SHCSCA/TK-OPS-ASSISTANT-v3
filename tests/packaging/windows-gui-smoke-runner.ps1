param(
    [Parameter(Mandatory = $true)]
    [string]$ScriptPath,
    [Parameter(Mandatory = $true)]
    [string]$DesktopPath,
    [Parameter(Mandatory = $true)]
    [string]$PortableZipPath,
    [Parameter(Mandatory = $true)]
    [string]$EvidencePath
)

$ErrorActionPreference = "Stop"
$source = Get-Content -LiteralPath $ScriptPath -Raw -Encoding UTF8
$script = [ScriptBlock]::Create($source)
& $script `
    -DesktopPath $DesktopPath `
    -PortableZipPath $PortableZipPath `
    -EvidencePath $EvidencePath
