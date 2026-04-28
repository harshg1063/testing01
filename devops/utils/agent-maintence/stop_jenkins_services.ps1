# PowerShell script to stop Jenkins services (device-agnostic)
# Kills Selenium Grid, Selenium Node, and any node.exe processes

$deviceName = $env:COMPUTERNAME
Write-Host "Stopping Jenkins services on device: $deviceName"

# Find and stop any process using port 4444 (Selenium Grid port)
$port4444 = Get-NetTCPConnection -LocalPort 4444 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($port4444) {
    $processId = $port4444.OwningProcess
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "Stopping process using port 4444: $($process.Name) (PID: $processId)"
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
        } catch {
            Write-Warning "Failed to stop process with Stop-Process, trying taskkill: $_"
            & taskkill /F /PID $processId 2>&1 | Out-Null
        }
    }
} else {
    Write-Host "No process found on port 4444"
}

# Find and stop any process using port 10050 (Selenium Node/relay port)
$port10050 = Get-NetTCPConnection -LocalPort 10050 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($port10050) {
    $processId = $port10050.OwningProcess
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "Stopping process using port 10050: $($process.Name) (PID: $processId)"
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
        } catch {
            Write-Warning "Failed to stop process with Stop-Process, trying taskkill: $_"
            & taskkill /F /PID $processId 2>&1 | Out-Null
        }
    }
} else {
    Write-Host "No process found on port 10050"
}

# Stop all node.exe processes (catches any remaining Appium instances)
Get-Process -Name "node" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "Stopping node process: $($_.Id)"
    try {
        Stop-Process -Id $_.Id -Force -ErrorAction Stop
    } catch {
        Write-Warning "Failed to stop node process $($_.Id), trying taskkill"
        & taskkill /F /PID $_.Id 2>&1 | Out-Null
    }
}

# Close any lingering PowerShell windows that might be empty after killing processes
Get-Process -Name "powershell" -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -ne "" } | ForEach-Object {
    # Check if the window title contains selenium/java indicators or is just an empty admin window
    if ($_.MainWindowTitle -match "Administrator.*PowerShell" -or $_.MainWindowTitle -match "powershell") {
        Write-Host "Closing PowerShell window: $($_.MainWindowTitle) (PID: $($_.Id))"
        try {
            $_.CloseMainWindow() | Out-Null
            Start-Sleep -Milliseconds 500
            if (-not $_.HasExited) {
                Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
            }
        } catch {
            Write-Warning "Failed to close PowerShell window: $_"
        }
    }
}

Write-Host "Jenkins services stop script completed."
