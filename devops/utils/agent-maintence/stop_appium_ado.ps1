
# PowerShell script to stop Appium and Selenium/relay Java processes for ADO (device-agnostic)
$deviceName = $env:COMPUTERNAME
Write-Host "Stopping Appium and Selenium/relay Java processes for ADO on device: $deviceName"

# Find and stop any process using port 11000 (Appium port)
$port11000 = Get-NetTCPConnection -LocalPort 11000 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($port11000) {
    $processId = $port11000.OwningProcess
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "Stopping process using port 11000: $($process.Name) (PID: $processId)"
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
        } catch {
            Write-Warning "Failed to stop process with Stop-Process, trying taskkill: $_"
            & taskkill /F /PID $processId 2>&1 | Out-Null
        }
    }
}

# Stop all Appium processes by name
Get-Process -Name "Appium" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "Stopping Appium process: $($_.Id)"
    try {
        Stop-Process -Id $_.Id -Force -ErrorAction Stop
    } catch {
        Write-Warning "Failed to stop Appium process $($_.Id), trying taskkill"
        & taskkill /F /PID $_.Id 2>&1 | Out-Null
    }
}

# Stop all node.exe processes (Appium runs on Node.js)
Get-Process -Name "node" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "Stopping node process: $($_.Id)"
    try {
        Stop-Process -Id $_.Id -Force -ErrorAction Stop
    } catch {
        Write-Warning "Failed to stop node process $($_.Id), trying taskkill"
        & taskkill /F /PID $_.Id 2>&1 | Out-Null
    }
}

# Stop all Selenium/relay java processes (with 'selenium' in command line)
Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "java.exe" -and $_.CommandLine -match "selenium" } | ForEach-Object {
    Write-Host "Stopping Selenium/relay process: $($_.ProcessId) $($_.CommandLine)"
    try {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
    } catch {
        Write-Warning "Failed to stop Java process $($_.ProcessId), trying taskkill"
        & taskkill /F /PID $_.ProcessId 2>&1 | Out-Null
    }
}

Write-Host "Stop script completed."
