<#
Runs pytest with device settings from scripts\devices.json so you can pass -Device names
instead of typing host/port/target each time.

Examples:
    powershell -ExecutionPolicy Bypass -File .\scripts\run-asqe.ps1 -TestPath tests\hp_app\video_control\test_x.py -Device Goldy
    powershell -ExecutionPolicy Bypass -File .\scripts\run-asqe.ps1 -TestPath tests\hp_app\video_control\test_x.py -Device Sammy,Goldy -NewWindow
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$TestPath,

    [string[]]$Device,

    [string]$RepoPath,
    
    [string]$Install,

    [string]$PytestArgs = "",

    [switch]$NewWindow,

    [string]$PythonExe
)

# Resolve repo root (parent of scripts) and validate it exists.
$defaultRepoPath = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
if (-not $RepoPath) {
    $RepoPath = $defaultRepoPath.Path
}
$RepoPath = [System.IO.Path]::GetFullPath($RepoPath)
if (-not (Test-Path -LiteralPath $RepoPath)) {
    Write-Warning "RepoPath does not exist: $RepoPath. Falling back to default repo root."
    $RepoPath = $defaultRepoPath.Path
}

# Prefer venv Python if available, otherwise use default python.
if (-not $PythonExe) {
    $venvPython = Join-Path $RepoPath "venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        $PythonExe = $venvPython
    } else {
        $PythonExe = "python"
    }
}

# Load device definitions from scripts/devices.json.
$devicesFile = Join-Path $PSScriptRoot "devices.json"
if (-not (Test-Path $devicesFile)) {
    throw "Devices file not found: $devicesFile"
}

$devices = Get-Content $devicesFile -Raw | ConvertFrom-Json
if (-not $devices) {
    throw "No devices found in $devicesFile"
}

# Build a name -> device info lookup.
$deviceMap = @{}
foreach ($d in $devices) {
    if ($null -ne $d.name) {
        $deviceMap[$d.name] = $d
    }
}

# Use provided device(s); otherwise pick one at random.
$targets = @()
if ($Device -and $Device.Count -gt 0) {
    foreach ($item in $Device) {
        $targets += ($item -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    }
} else {
    $targets = @((Get-Random -InputObject $deviceMap.Keys))
}

foreach ($name in $targets) {
    if (-not $deviceMap.ContainsKey($name)) {
        throw "Device '$name' not found in $devicesFile"
    }

    $d = $deviceMap[$name]
    $executorUrl = $d.url
    $executorPort = $d.port
    $testTarget = $d.target

    if (-not $executorUrl -or -not $executorPort -or -not $testTarget) {
        throw "Device '$name' is missing url/port/target in $devicesFile"
    }

    # Resolve test path relative to repo root if needed.
    $resolvedTestPath = if ([System.IO.Path]::IsPathRooted($TestPath)) {
        $TestPath
    } else {
        Join-Path $RepoPath $TestPath
    }

    # Build the pytest command with device-specific host/port/target.
    $installArg = if ($Install) { "--install $Install" } else { "" }
    $cmd = "$PythonExe -m pytest --test-target $testTarget --executor-url $executorUrl --executor-port $executorPort $resolvedTestPath $installArg $PytestArgs"

    # Optionally run each device in a new PowerShell window.
    if ($NewWindow) {
        Start-Process powershell.exe -WorkingDirectory $RepoPath -ArgumentList "-NoExit", "-Command", $cmd
    } else {
        Push-Location $RepoPath
        try {
            Invoke-Expression $cmd
        } finally {
            Pop-Location
        }
    }
}