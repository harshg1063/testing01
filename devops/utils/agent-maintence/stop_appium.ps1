# PowerShell script to stop all Appium processes (both Jenkins and ADO setups)
$deviceName = $env:COMPUTERNAME
Write-Host "Stopping all Appium processes on device: $deviceName"

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

# Stop Appium by process name (standalone or service)
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

Write-Host "Appium stop script completed."
