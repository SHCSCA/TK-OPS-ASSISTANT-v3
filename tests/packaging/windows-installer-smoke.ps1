param(
    [string]$InstallerPath = "",
    [switch]$KeepArtifactsOnFailure
)

$ErrorActionPreference = "Stop"
$smokeScriptRoot = if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    Join-Path (Get-Location).Path "tests\packaging"
}
else {
    $PSScriptRoot
}
$desktopExecutableName = "tk-ops-desktop.exe"

function Resolve-InstallerPath {
    param([string]$ConfiguredPath)

    if ($ConfiguredPath) {
        $resolved = (Resolve-Path -LiteralPath $ConfiguredPath).Path
        if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
            throw "安装包不存在：$resolved"
        }
        return $resolved
    }

    $bundleRoot = Join-Path $smokeScriptRoot "..\..\apps\desktop\src-tauri\target\release\bundle\nsis"
    if (-not (Test-Path -LiteralPath $bundleRoot -PathType Container)) {
        throw "NSIS 安装包目录不存在，请先完成 Tauri NSIS 构建"
    }
    $candidate = Get-ChildItem -LiteralPath $bundleRoot -Filter "*-setup.exe" -File |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1
    if ($null -eq $candidate) {
        throw "没有找到 NSIS 安装包"
    }
    return $candidate.FullName
}

function Get-ScopedProcesses {
    param(
        [string]$InstallRoot,
        [string]$NamePattern
    )

    $normalizedRoot = [System.IO.Path]::GetFullPath($InstallRoot).TrimEnd("\") + "\"
    return @(
        Get-CimInstance Win32_Process -Filter "Name LIKE '$NamePattern'" |
            Where-Object {
                $_.ExecutablePath -and
                [System.IO.Path]::GetFullPath($_.ExecutablePath).StartsWith(
                    $normalizedRoot,
                    [System.StringComparison]::OrdinalIgnoreCase
                )
            }
    )
}

function Get-ScopedProcessIds {
    param(
        [string]$InstallRoot,
        [string]$NamePattern
    )

    return @(
        Get-ScopedProcesses -InstallRoot $InstallRoot -NamePattern $NamePattern |
            Sort-Object ProcessId |
            ForEach-Object { [int]$_.ProcessId }
    )
}

function Wait-ForStableScopedProcessIds {
    param(
        [string]$InstallRoot,
        [string]$NamePattern,
        [int]$TimeoutSeconds,
        [string]$FailureMessage
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $previousKey = $null
    $stableSamples = 0
    do {
        $processIds = @(
            Get-ScopedProcessIds -InstallRoot $InstallRoot -NamePattern $NamePattern
        )
        $currentKey = $processIds -join ","
        if ($processIds.Count -gt 0 -and $currentKey -eq $previousKey) {
            $stableSamples += 1
        }
        else {
            $stableSamples = 0
            $previousKey = $currentKey
        }
        if ($stableSamples -ge 4) {
            return $processIds
        }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    throw $FailureMessage
}

function Wait-ForDesktopProcessQuietPeriod {
    param(
        [string]$ProcessName,
        [int]$TimeoutSeconds,
        [string]$FailureMessage
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $quietSamples = 0
    do {
        $processCount = @(
            Get-CimInstance Win32_Process -Filter "Name = '$ProcessName'"
        ).Count
        if ($processCount -eq 0) {
            $quietSamples += 1
        }
        else {
            $quietSamples = 0
        }
        if ($quietSamples -ge 4) {
            return
        }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    throw $FailureMessage
}

function Wait-ForCondition {
    param(
        [scriptblock]$Condition,
        [int]$TimeoutSeconds,
        [string]$FailureMessage
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    do {
        if (& $Condition) {
            return
        }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    throw $FailureMessage
}

function Get-BoundedJsonLogRecords {
    param(
        [string]$LogPath,
        [int]$TailCount = 300,
        [long]$MaxBytes = 8388608
    )

    if (-not (Test-Path -LiteralPath $LogPath -PathType Leaf)) {
        return @()
    }
    try {
        $item = Get-Item -LiteralPath $LogPath -ErrorAction Stop
        if ($item.Length -le 0 -or $item.Length -gt $MaxBytes) {
            return @()
        }
        $lines = @(
            Get-Content `
                -LiteralPath $LogPath `
                -Encoding UTF8 `
                -Tail $TailCount `
                -ErrorAction Stop
        )
    }
    catch {
        return @()
    }

    $records = @()
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        try {
            $record = $line | ConvertFrom-Json -ErrorAction Stop
            if ($null -ne $record) {
                $records += $record
            }
        }
        catch {
            continue
        }
    }
    return $records
}

function Test-SupervisorReadyEvidence {
    param([string]$LogPath)

    $records = Get-BoundedJsonLogRecords -LogPath $LogPath
    foreach ($record in $records) {
        if (
            $record.module -eq "tauri.runtime_supervisor" -and
            $record.level -eq "info" -and
            $record.operation -eq "runtime.ready" -and
            $null -eq $record.errorCode
        ) {
            return $true
        }
    }
    return $false
}

function Test-RuntimeProductionEvidence {
    param([string]$LogPath)

    $records = Get-BoundedJsonLogRecords -LogPath $LogPath
    foreach ($record in $records) {
        if (
            $record.operation -eq "runtime.started" -and
            $record.context.mode -eq "production" -and
            $record.context.databaseReady -eq $true
        ) {
            return $true
        }
    }
    return $false
}

function Get-SafeSupervisorFailureSummary {
    param([string]$LogPath)

    $record = Get-BoundedJsonLogRecords -LogPath $LogPath |
        Where-Object { $null -ne $_.errorCode } |
        Select-Object -Last 1
    if ($null -eq $record) {
        return $null
    }

    $operation = [string]$record.operation
    if ($operation -notmatch "^[a-z0-9._-]{1,96}$") {
        $operation = "runtime.failure"
    }
    $errorCode = [string]$record.errorCode
    if ($errorCode -notmatch "^[A-Z0-9._-]{1,96}$") {
        $errorCode = "RUNTIME_STARTUP_FAILED"
    }
    $logId = [string]$record.logId
    if ($logId -notmatch "^[A-Za-z0-9_-]{1,96}$") {
        $logId = "不可用"
    }
    return "operation=$operation errorCode=$errorCode logId=$logId"
}

function Get-SafeMigrationFailureSummary {
    param(
        [string]$JournalPath,
        [long]$MaxBytes = 2097152
    )

    if (-not (Test-Path -LiteralPath $JournalPath -PathType Leaf)) {
        return $null
    }
    try {
        $item = Get-Item -LiteralPath $JournalPath -ErrorAction Stop
        if ($item.Length -le 0 -or $item.Length -gt $MaxBytes) {
            return $null
        }
        $document = Get-Content `
            -LiteralPath $JournalPath `
            -Raw `
            -Encoding UTF8 `
            -ErrorAction Stop |
            ConvertFrom-Json -ErrorAction Stop
        if ($document.formatVersion -ne 1 -or $null -eq $document.events) {
            return $null
        }
        $event = $document.events |
            Where-Object { $_.stage -eq "migration_failed" } |
            Select-Object -Last 1
        if ($null -eq $event) {
            return $null
        }
    }
    catch {
        return $null
    }

    $errorType = [string]$event.evidence.errorType
    if ($errorType -notmatch "^[A-Za-z][A-Za-z0-9_]{0,95}$") {
        $errorType = "UnknownError"
    }
    $mutationStarted = $event.evidence.mutationStarted -eq $true
    $automaticRestoreAllowed = (
        $event.evidence.automaticRestoreAllowed -eq $true
    )
    $currentRevision = [string]$event.evidence.currentRevision
    if ($currentRevision -notmatch "^[0-9]{4}_[a-z0-9_]{1,96}$") {
        $currentRevision = "unknown"
    }
    $sqliteErrorName = [string]$event.evidence.sqliteErrorName
    if ($sqliteErrorName -notmatch "^SQLITE_[A-Z0-9_]{1,64}$") {
        $sqliteErrorName = "SQLITE_UNKNOWN"
    }
    return (
        "errorType=$errorType currentRevision=$currentRevision " +
        "sqliteErrorName=$sqliteErrorName mutationStarted=$mutationStarted " +
        "automaticRestoreAllowed=$automaticRestoreAllowed"
    )
}

function Test-SqliteDatabase {
    param([string]$DatabasePath)

    if (-not (Test-Path -LiteralPath $DatabasePath -PathType Leaf)) {
        return $false
    }
    $stream = $null
    try {
        $stream = [System.IO.File]::Open(
            $DatabasePath,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::ReadWrite
        )
        $header = New-Object byte[] 16
        if ($stream.Read($header, 0, $header.Length) -ne $header.Length) {
            return $false
        }
        $expected = [byte[]](
            83, 81, 76, 105, 116, 101, 32, 102,
            111, 114, 109, 97, 116, 32, 51, 0
        )
        for ($index = 0; $index -lt $expected.Length; $index++) {
            if ($header[$index] -ne $expected[$index]) {
                return $false
            }
        }
        return $true
    }
    catch {
        return $false
    }
    finally {
        if ($null -ne $stream) {
            $stream.Dispose()
        }
    }
}

function Assert-ArtifactWithinRoot {
    param(
        [string]$ArtifactPath,
        [string]$ExpectedRoot,
        [string]$Description
    )

    if (-not (Test-Path -LiteralPath $ArtifactPath -PathType Leaf)) {
        throw "$Description 不存在"
    }
    $normalizedRoot = [System.IO.Path]::GetFullPath(
        $ExpectedRoot
    ).TrimEnd("\") + "\"
    $resolvedArtifact = (Resolve-Path -LiteralPath $ArtifactPath).Path
    if (
        -not $resolvedArtifact.StartsWith(
            $normalizedRoot,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        throw "$Description 未落在安装包验收数据目录"
    }
    if ((Get-Item -LiteralPath $resolvedArtifact).Length -le 0) {
        throw "$Description 为空"
    }
}

function Stop-ScopedProcesses {
    param([string]$InstallRoot)

    $processes = @(
        Get-ScopedProcesses -InstallRoot $InstallRoot -NamePattern $desktopExecutableName
    ) + @(
        Get-ScopedProcesses -InstallRoot $InstallRoot -NamePattern "tk-ops-runtime%.exe"
    )
    foreach ($process in $processes) {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

$installer = Resolve-InstallerPath -ConfiguredPath $InstallerPath
$smokeRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
    "tk-ops-installer-smoke-" + [Guid]::NewGuid().ToString("N")
)
$installRoot = Join-Path $smokeRoot "app"
$dataRoot = Join-Path $smokeRoot "data"
$originalPath = $env:PATH
$hadSmokeFlag = Test-Path Env:TK_OPS_INSTALLER_SMOKE
$originalSmokeFlag = $env:TK_OPS_INSTALLER_SMOKE
$hadSmokeDataDir = Test-Path Env:TK_OPS_INSTALLER_SMOKE_DATA_DIR
$originalSmokeDataDir = $env:TK_OPS_INSTALLER_SMOKE_DATA_DIR
$firstProcess = $null
$smokeSucceeded = $false
$currentStage = "initialize"

try {
    New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $dataRoot -Force | Out-Null

    $currentStage = "silent-install"
    $install = Start-Process `
        -FilePath $installer `
        -ArgumentList @("/S", "/D=$installRoot") `
        -PassThru `
        -Wait `
        -WindowStyle Hidden
    if ($install.ExitCode -ne 0) {
        throw "NSIS 静默安装失败，退出码 $($install.ExitCode)"
    }

    $desktopBinary = Join-Path $installRoot $desktopExecutableName
    if (-not (Test-Path -LiteralPath $desktopBinary -PathType Leaf)) {
        throw "安装后缺少 $desktopExecutableName"
    }

    $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
    $env:TK_OPS_INSTALLER_SMOKE = "1"
    $env:TK_OPS_INSTALLER_SMOKE_DATA_DIR = $dataRoot
    $supervisorLog = Join-Path $dataRoot "logs\runtime-supervisor.jsonl"
    $runtimeDataRoot = Join-Path $dataRoot "runtime"
    $runtimeDatabase = Join-Path $runtimeDataRoot "runtime.db"
    $runtimeLog = Join-Path $runtimeDataRoot "logs\runtime.jsonl"
    $migrationJournal = Join-Path `
        $runtimeDataRoot `
        ".runtime.db.migrations\cutover-journal.json"

    $currentStage = "desktop-quiet-before-launch"
    Wait-ForDesktopProcessQuietPeriod `
        -ProcessName $desktopExecutableName `
        -TimeoutSeconds 15 `
        -FailureMessage "已有 TK-OPS Desktop 实例正在运行，无法执行安装包验收"
    $firstProcess = Start-Process `
        -FilePath $desktopBinary `
        -PassThru

    $currentStage = "runtime-sidecar-start"
    Wait-ForCondition -TimeoutSeconds 45 -FailureMessage "安装后的 Runtime sidecar 未启动" -Condition {
        $firstProcess.Refresh()
        if ($firstProcess.HasExited) {
            throw "Desktop 在 Runtime sidecar 启动前退出，退出码 $($firstProcess.ExitCode)"
        }
        (Get-ScopedProcesses -InstallRoot $installRoot -NamePattern "tk-ops-runtime%.exe").Count -ge 1
    }
    try {
        $currentStage = "runtime-supervisor-ready"
        Wait-ForCondition `
            -TimeoutSeconds 90 `
            -FailureMessage "Supervisor 未在时限内达到 runtime.ready" `
            -Condition {
                $firstProcess.Refresh()
                if ($firstProcess.HasExited) {
                    throw "Desktop 在 runtime.ready 前退出，退出码 $($firstProcess.ExitCode)"
                }
                Test-SupervisorReadyEvidence -LogPath $supervisorLog
            }
    }
    catch {
        $safeFailure = Get-SafeSupervisorFailureSummary -LogPath $supervisorLog
        $migrationFailure = Get-SafeMigrationFailureSummary `
            -JournalPath $migrationJournal
        if ($null -ne $safeFailure) {
            if ($null -ne $migrationFailure) {
                throw "Supervisor 未就绪：$safeFailure $migrationFailure"
            }
            throw "Supervisor 未就绪：$safeFailure"
        }
        throw
    }

    $currentStage = "runtime-production-evidence"
    Wait-ForCondition `
        -TimeoutSeconds 20 `
        -FailureMessage "production Runtime 数据或启动日志未落入指定目录" `
        -Condition {
            (Test-SqliteDatabase -DatabasePath $runtimeDatabase) -and
            (Test-RuntimeProductionEvidence -LogPath $runtimeLog)
        }
    Assert-ArtifactWithinRoot `
        -ArtifactPath $supervisorLog `
        -ExpectedRoot $dataRoot `
        -Description "Supervisor ready 日志"
    Assert-ArtifactWithinRoot `
        -ArtifactPath $runtimeDatabase `
        -ExpectedRoot $dataRoot `
        -Description "production Runtime 数据库"
    Assert-ArtifactWithinRoot `
        -ArtifactPath $runtimeLog `
        -ExpectedRoot $dataRoot `
        -Description "production Runtime 日志"

    # PyInstaller 单文件 Runtime 启动初期会先出现引导进程，必须等待进程集合稳定。
    $currentStage = "runtime-process-stable"
    $runtimeProcessIds = @(
        Wait-ForStableScopedProcessIds `
            -InstallRoot $installRoot `
            -NamePattern "tk-ops-runtime%.exe" `
            -TimeoutSeconds 20 `
            -FailureMessage "Runtime sidecar 进程集合未能稳定"
    )

    $currentStage = "single-instance-exit"
    $secondProcess = Start-Process `
        -FilePath $desktopBinary `
        -PassThru
    Wait-ForCondition -TimeoutSeconds 15 -FailureMessage "第二实例没有被单实例边界关闭" -Condition {
        $secondProcess.Refresh()
        $secondProcess.HasExited
    }
    $currentStage = "single-instance-runtime-converge"
    Wait-ForCondition `
        -TimeoutSeconds 20 `
        -FailureMessage "第二实例启动的额外 Runtime sidecar 未及时退出" `
        -Condition {
            $currentProcessIds = @(
                Get-ScopedProcessIds `
                    -InstallRoot $installRoot `
                    -NamePattern "tk-ops-runtime%.exe"
            )
            if ($currentProcessIds.Count -ne $runtimeProcessIds.Count) {
                return $false
            }
            return @(
                Compare-Object `
                    -ReferenceObject $runtimeProcessIds `
                    -DifferenceObject $currentProcessIds
            ).Count -eq 0
        }

    $currentStage = "desktop-graceful-close"
    if (-not $firstProcess.CloseMainWindow()) {
        throw "无法向桌面主窗口发送优雅退出请求"
    }
    Wait-ForCondition -TimeoutSeconds 20 -FailureMessage "桌面主进程未在时限内退出" -Condition {
        $firstProcess.Refresh()
        $firstProcess.HasExited
    }
    $currentStage = "runtime-tree-close"
    Wait-ForCondition -TimeoutSeconds 20 -FailureMessage "桌面退出后 Runtime 进程树仍存在" -Condition {
        (Get-ScopedProcesses -InstallRoot $installRoot -NamePattern "tk-ops-runtime%.exe").Count -eq 0
    }
    $currentStage = "single-instance-release"
    Wait-ForDesktopProcessQuietPeriod `
        -ProcessName $desktopExecutableName `
        -TimeoutSeconds 15 `
        -FailureMessage "桌面退出后单实例边界未释放"

    Write-Host (
        "[installer-smoke] 通过：Supervisor ready、production 数据落点、" +
        "离线启动、单实例与进程树清理"
    )
    $smokeSucceeded = $true
}
catch {
    [Console]::Error.WriteLine(
        "[installer-smoke] failed stage=$currentStage message=$($_.Exception.Message)"
    )
    throw
}
finally {
    $env:PATH = $originalPath
    if ($hadSmokeFlag) {
        $env:TK_OPS_INSTALLER_SMOKE = $originalSmokeFlag
    }
    else {
        Remove-Item Env:TK_OPS_INSTALLER_SMOKE -ErrorAction SilentlyContinue
    }
    if ($hadSmokeDataDir) {
        $env:TK_OPS_INSTALLER_SMOKE_DATA_DIR = $originalSmokeDataDir
    }
    else {
        Remove-Item Env:TK_OPS_INSTALLER_SMOKE_DATA_DIR -ErrorAction SilentlyContinue
    }
    Stop-ScopedProcesses -InstallRoot $installRoot

    $uninstaller = Join-Path $installRoot "uninstall.exe"
    if (Test-Path -LiteralPath $uninstaller -PathType Leaf) {
        Start-Process `
            -FilePath $uninstaller `
            -ArgumentList "/S" `
            -Wait `
            -WindowStyle Hidden
    }

    $resolvedSmokeRoot = [System.IO.Path]::GetFullPath($smokeRoot)
    $resolvedTempRoot = [System.IO.Path]::GetFullPath(
        [System.IO.Path]::GetTempPath()
    ).TrimEnd("\") + "\"
    $safeSmokeRoot =
        $resolvedSmokeRoot.StartsWith(
            $resolvedTempRoot,
            [System.StringComparison]::OrdinalIgnoreCase
        ) -and
        [System.IO.Path]::GetFileName($resolvedSmokeRoot).StartsWith(
            "tk-ops-installer-smoke-",
            [System.StringComparison]::Ordinal
        )
    if ($safeSmokeRoot -and ($smokeSucceeded -or -not $KeepArtifactsOnFailure)) {
        Remove-Item -LiteralPath $resolvedSmokeRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    elseif ($safeSmokeRoot) {
        Write-Warning "安装包验收失败证据已保留：$resolvedSmokeRoot"
    }
}
