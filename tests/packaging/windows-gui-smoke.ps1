param(
    [Parameter(Mandatory = $true)]
    [string]$DesktopPath,
    [Parameter(Mandatory = $true)]
    [string]$PortableZipPath,
    [Parameter(Mandatory = $true)]
    [string]$EvidencePath,
    [switch]$KeepArtifactsOnFailure
)

$ErrorActionPreference = "Stop"

Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public static class TkOpsWindowProbe
{
    public const int GWL_STYLE = -16;
    public const int SW_MAXIMIZE = 3;
    public const int SW_MINIMIZE = 6;
    public const int SW_RESTORE = 9;
    public const uint WM_CLOSE = 0x0010;

    [DllImport("user32.dll", SetLastError = true)]
    public static extern int GetWindowLong(IntPtr hWnd, int nIndex);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool IsWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool IsIconic(IntPtr hWnd);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool IsZoomed(IntPtr hWnd);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool PostMessage(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam);

    private delegate bool EnumWindowProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool EnumChildWindows(IntPtr parent, EnumWindowProc callback, IntPtr lParam);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool EnumWindows(EnumWindowProc callback, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetClassName(IntPtr hWnd, StringBuilder className, int maxCount);

    public static string[] ChildWindowClasses(IntPtr parent)
    {
        var classes = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        EnumChildWindows(parent, (window, _) => {
            var value = new StringBuilder(256);
            if (GetClassName(window, value, value.Capacity) > 0) {
                classes.Add(value.ToString());
            }
            return true;
        }, IntPtr.Zero);
        var result = new string[classes.Count];
        classes.CopyTo(result);
        return result;
    }

    public static IntPtr[] TopLevelWindows(uint processId)
    {
        var windows = new List<IntPtr>();
        EnumWindows((window, _) => {
            uint ownerProcessId;
            GetWindowThreadProcessId(window, out ownerProcessId);
            if (ownerProcessId == processId) {
                windows.Add(window);
            }
            return true;
        }, IntPtr.Zero);
        return windows.ToArray();
    }
}
"@

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

function Get-ScopedRuntimeProcesses {
    param([string]$BinaryRoot)

    $normalizedRoot = [System.IO.Path]::GetFullPath($BinaryRoot).TrimEnd("\") + "\"
    return @(
        Get-CimInstance Win32_Process -Filter "Name = 'tk-ops-runtime.exe'" |
            Where-Object {
                $_.ExecutablePath -and
                [System.IO.Path]::GetFullPath($_.ExecutablePath).StartsWith(
                    $normalizedRoot,
                    [System.StringComparison]::OrdinalIgnoreCase
                )
            }
    )
}

function Get-ScopedRuntimeProcessRoots {
    param([string]$BinaryRoot)

    $processes = @(Get-ScopedRuntimeProcesses -BinaryRoot $BinaryRoot)
    $ids = @{}
    foreach ($process in $processes) {
        $ids[[int]$process.ProcessId] = $true
    }
    return @(
        $processes | Where-Object {
            -not $ids.ContainsKey([int]$_.ParentProcessId)
        }
    )
}

function Get-ReadyEventCount {
    param([string]$LogPath)

    if (-not (Test-Path -LiteralPath $LogPath -PathType Leaf)) {
        return 0
    }
    $count = 0
    foreach ($line in Get-Content -LiteralPath $LogPath -Encoding UTF8 -Tail 500) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        try {
            $record = $line | ConvertFrom-Json -ErrorAction Stop
            if (
                $record.module -eq "tauri.runtime_supervisor" -and
                $record.operation -eq "runtime.ready" -and
                $record.level -eq "info"
            ) {
                $count += 1
            }
        }
        catch {
            continue
        }
    }
    return $count
}

function Get-Sha256 {
    param([string]$Path)

    $stream = [System.IO.File]::OpenRead($Path)
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = $hasher.ComputeHash($stream)
        return ([System.BitConverter]::ToString($hash)).Replace("-", "")
    }
    finally {
        $hasher.Dispose()
        $stream.Dispose()
    }
}

function Get-MainWindowHandle {
    param([System.Diagnostics.Process]$Process)

    $Process.Refresh()
    foreach ($candidate in [TkOpsWindowProbe]::TopLevelWindows($Process.Id)) {
        if (-not [TkOpsWindowProbe]::IsWindowVisible($candidate)) {
            continue
        }
        $childClasses = [TkOpsWindowProbe]::ChildWindowClasses($candidate)
        $hasWebView = @($childClasses | Where-Object {
            $_ -like "Chrome_*" -or $_ -like "*WebView*"
        }).Count -gt 0
        if ($hasWebView) {
            return $candidate
        }
    }
    return $Process.MainWindowHandle
}

function Close-WindowGracefully {
    param([System.Diagnostics.Process]$Process)

    $handle = Get-MainWindowHandle -Process $Process
    if ($handle -eq [IntPtr]::Zero) {
        throw "桌面主窗口句柄不可用，无法执行 WM_CLOSE"
    }
    if (-not [TkOpsWindowProbe]::PostMessage(
        $handle,
        [TkOpsWindowProbe]::WM_CLOSE,
        [IntPtr]::Zero,
        [IntPtr]::Zero
    )) {
        throw "发送 WM_CLOSE 失败"
    }
    Wait-ForCondition -TimeoutSeconds 20 -FailureMessage "Desktop 未响应 WM_CLOSE" -Condition {
        $Process.Refresh()
        $Process.HasExited
    }
}

function Wait-ForStandardWindow {
    param(
        [System.Diagnostics.Process]$Process,
        [int]$TimeoutSeconds = 30
    )

    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    $requiredStyle = 0x00010000 -bor 0x00020000 -bor 0x00040000 -bor 0x00080000
    $lastHandle = [IntPtr]::Zero
    $stableSamples = 0
    do {
        $candidate = Get-MainWindowHandle -Process $Process
        $isUsable =
            $candidate -ne [IntPtr]::Zero -and
            [TkOpsWindowProbe]::IsWindow($candidate) -and
            [TkOpsWindowProbe]::IsWindowVisible($candidate)
        if ($isUsable) {
            $currentStyle = [TkOpsWindowProbe]::GetWindowLong(
                $candidate,
                [TkOpsWindowProbe]::GWL_STYLE
            )
            $isUsable = ($currentStyle -band $requiredStyle) -eq $requiredStyle
        }
        if ($isUsable) {
            if ($candidate -eq $lastHandle) {
                $stableSamples += 1
            }
            else {
                $lastHandle = $candidate
                $stableSamples = 1
            }
            if ($stableSamples -ge 3) {
                return $candidate
            }
        }
        else {
            $lastHandle = [IntPtr]::Zero
            $stableSamples = 0
        }
        Start-Sleep -Milliseconds 250
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "主窗口未在时限内稳定启用标准窗口控制"
}

function Assert-VisibleWindow {
    param([System.Diagnostics.Process]$Process)

    Wait-ForCondition -TimeoutSeconds 30 -FailureMessage "Desktop 可见主窗口未出现" -Condition {
        $handle = Get-MainWindowHandle -Process $Process
        $handle -ne [IntPtr]::Zero -and [TkOpsWindowProbe]::IsWindowVisible($handle)
    }
    $handle = Wait-ForStandardWindow -Process $Process
    [TkOpsWindowProbe]::ShowWindow($handle, [TkOpsWindowProbe]::SW_MINIMIZE) | Out-Null
    Wait-ForCondition -TimeoutSeconds 10 -FailureMessage "主窗口无法最小化" -Condition {
        [TkOpsWindowProbe]::IsIconic($handle)
    }
    [TkOpsWindowProbe]::ShowWindow($handle, [TkOpsWindowProbe]::SW_MAXIMIZE) | Out-Null
    Wait-ForCondition -TimeoutSeconds 10 -FailureMessage "主窗口无法最大化" -Condition {
        [TkOpsWindowProbe]::IsZoomed($handle)
    }
    [TkOpsWindowProbe]::ShowWindow($handle, [TkOpsWindowProbe]::SW_RESTORE) | Out-Null
    return $handle
}

$sourceDesktop = (Resolve-Path -LiteralPath $DesktopPath).Path
$portableZip = (Resolve-Path -LiteralPath $PortableZipPath).Path
$evidence = [System.IO.Path]::GetFullPath($EvidencePath)
$smokeRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
    "tk-ops-gui-smoke-" + [Guid]::NewGuid().ToString("N")
)
$dataRoot = Join-Path $smokeRoot "data"
$extractRoot = Join-Path $smokeRoot "portable"
$desktop = $null
$binaryRoot = $null
$originalSmokeFlag = $env:TK_OPS_INSTALLER_SMOKE
$originalDataRoot = $env:TK_OPS_INSTALLER_SMOKE_DATA_DIR
$firstProcess = $null
$restartProcess = $null
$startedAt = [DateTime]::UtcNow.ToString("o")
$checks = New-Object System.Collections.Generic.List[string]
$smokeSucceeded = $false

try {
    New-Item -ItemType Directory -Path $dataRoot -Force | Out-Null
    New-Item -ItemType Directory -Path $extractRoot -Force | Out-Null
    Expand-Archive -LiteralPath $portableZip -DestinationPath $extractRoot
    $packageRoots = @(Get-ChildItem -LiteralPath $extractRoot -Directory)
    if ($packageRoots.Count -ne 1) {
        throw "免安装 ZIP 必须只包含一个顶层目录"
    }
    $binaryRoot = $packageRoots[0].FullName
    $rootExecutables = @(Get-ChildItem -LiteralPath $binaryRoot -Filter "*.exe" -File)
    if ($rootExecutables.Count -ne 1) {
        throw "免安装包根目录必须只有一个 Desktop EXE 用户入口"
    }
    $desktop = $rootExecutables[0].FullName
    if ((Get-Sha256 -Path $desktop) -ne (Get-Sha256 -Path $sourceDesktop)) {
        throw "全新解压 Desktop EXE 与本次构建制品不一致"
    }
    $sidecar = Join-Path $binaryRoot "resources\runtime\tk-ops-runtime.exe"
    if (-not (Test-Path -LiteralPath $sidecar -PathType Leaf)) {
        throw "内部资源目录缺少 tk-ops-runtime.exe"
    }
    $checks.Add("fresh-portable-extraction")
    $env:TK_OPS_INSTALLER_SMOKE = "1"
    $env:TK_OPS_INSTALLER_SMOKE_DATA_DIR = $dataRoot
    $supervisorLog = Join-Path $dataRoot "logs\runtime-supervisor.jsonl"

    $firstProcess = Start-Process -FilePath $desktop -PassThru
    $null = Assert-VisibleWindow -Process $firstProcess
    $checks.Add("visible-main-window")
    $checks.Add("single-root-executable")
    $checks.Add("standard-window-controls")
    $checks.Add("minimize-maximize-restore")

    Wait-ForCondition -TimeoutSeconds 90 -FailureMessage "Runtime Supervisor 未达到 ready" -Condition {
        (Get-ReadyEventCount -LogPath $supervisorLog) -ge 1
    }
    $checks.Add("runtime-ready")
    $runtimeCount = @(Get-ScopedRuntimeProcessRoots -BinaryRoot $binaryRoot).Count
    if ($runtimeCount -ne 1) {
        throw "首实例没有且仅有一个 Runtime sidecar 进程树"
    }

    $secondProcess = Start-Process -FilePath $desktop -PassThru
    Wait-ForCondition -TimeoutSeconds 10 -FailureMessage "第二 Desktop 实例未退出" -Condition {
        $secondProcess.Refresh()
        $secondProcess.HasExited
    }
    if (@(Get-ScopedRuntimeProcessRoots -BinaryRoot $binaryRoot).Count -ne 1) {
        throw "第二 Desktop 实例创建了额外 Runtime sidecar 进程树"
    }
    $checks.Add("single-instance")

    Close-WindowGracefully -Process $firstProcess
    Wait-ForCondition -TimeoutSeconds 20 -FailureMessage "WM_CLOSE 后 Runtime 仍在运行" -Condition {
        @(Get-ScopedRuntimeProcesses -BinaryRoot $binaryRoot).Count -eq 0
    }
    $checks.Add("graceful-close")

    $readyCountBeforeRestart = Get-ReadyEventCount -LogPath $supervisorLog
    $restartProcess = Start-Process -FilePath $desktop -PassThru
    $null = Assert-VisibleWindow -Process $restartProcess
    Wait-ForCondition -TimeoutSeconds 90 -FailureMessage "Desktop 重启后 Runtime 未恢复 ready" -Condition {
        (Get-ReadyEventCount -LogPath $supervisorLog) -gt $readyCountBeforeRestart
    }
    $checks.Add("restart-recovery")
    Close-WindowGracefully -Process $restartProcess
    Wait-ForCondition -TimeoutSeconds 20 -FailureMessage "重启实例关闭后 Runtime 仍在运行" -Condition {
        @(Get-ScopedRuntimeProcesses -BinaryRoot $binaryRoot).Count -eq 0
    }

    $document = [ordered]@{
        id = "windows-gui-smoke"
        command = "windows-gui-smoke.ps1"
        exitCode = 0
        tests = $checks.Count
        startedAt = $startedAt
        completedAt = [DateTime]::UtcNow.ToString("o")
        desktopSha256 = Get-Sha256 -Path $desktop
        portableSha256 = Get-Sha256 -Path $portableZip
        checks = @($checks)
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $evidence) -Force | Out-Null
    $json = $document | ConvertTo-Json -Depth 4
    [System.IO.File]::WriteAllText(
        $evidence,
        $json,
        (New-Object System.Text.UTF8Encoding($false))
    )
    Write-Host "[windows-gui-smoke] 通过：$($checks.Count) 项可见窗口检查"
    $smokeSucceeded = $true
}
finally {
    foreach ($process in @($firstProcess, $restartProcess)) {
        if ($null -eq $process) {
            continue
        }
        try {
            $process.Refresh()
            if (-not $process.HasExited) {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        }
        catch {
            continue
        }
    }
    if ($binaryRoot) {
        foreach ($runtime in Get-ScopedRuntimeProcesses -BinaryRoot $binaryRoot) {
            Stop-Process -Id $runtime.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
    if ($null -eq $originalSmokeFlag) {
        Remove-Item Env:TK_OPS_INSTALLER_SMOKE -ErrorAction SilentlyContinue
    }
    else {
        $env:TK_OPS_INSTALLER_SMOKE = $originalSmokeFlag
    }
    if ($null -eq $originalDataRoot) {
        Remove-Item Env:TK_OPS_INSTALLER_SMOKE_DATA_DIR -ErrorAction SilentlyContinue
    }
    else {
        $env:TK_OPS_INSTALLER_SMOKE_DATA_DIR = $originalDataRoot
    }
    $resolvedSmokeRoot = [System.IO.Path]::GetFullPath($smokeRoot)
    $tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd("\") + "\"
    $safeSmokeRoot =
        $resolvedSmokeRoot.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase) -and
        [System.IO.Path]::GetFileName($resolvedSmokeRoot).StartsWith(
            "tk-ops-gui-smoke-",
            [System.StringComparison]::Ordinal
        )
    if ($safeSmokeRoot -and ($smokeSucceeded -or -not $KeepArtifactsOnFailure)) {
        Remove-Item -LiteralPath $resolvedSmokeRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    elseif ($safeSmokeRoot) {
        Write-Warning "GUI 验收失败证据已保留：$resolvedSmokeRoot"
    }
}
