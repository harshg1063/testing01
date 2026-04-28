# Appium Server Management Script
# Checks if Appium server is running on port 11000 and starts it if needed
# Parameters:
#   -AgentName: Optional agent name for logging context
#   -FeatureToTest: Optional feature name for logging context
#   -Mode: "specific-device", "matrix", or "default"

param(
    [string]$AgentName = "",
    [string]$FeatureToTest = "",
    [string]$Mode = "default"
)

$DebugPreference = "SilentlyContinue"
$ErrorActionPreference = "Stop"

# Log execution context
switch ($Mode) {
    "specific-device" {
        Write-Host "🎯 Executing on SPECIFIC DEVICE: $AgentName"
        Write-Host "Running on single agent with Name capability: $AgentName"
    }
    "matrix" {
        Write-Host "🎯 Executing on agent: $AgentName (part of matrix execution)"
        Write-Host "Feature being tested: $FeatureToTest"
    }
    default {
        Write-Host "🎯 Executing on agent: $AgentName"
    }
}
Write-Host ""

Write-Host "Checking if Appium server is running on port 11000..."

# Check if port 11000 is in use by Appium process
$portInUse = Get-NetTCPConnection -LocalPort 11000 -State Listen -ErrorAction SilentlyContinue
$appiumProcess = Get-Process -Name "node" -ErrorAction SilentlyContinue

if ($portInUse -and $appiumProcess) {
    Write-Host "Appium server is running (PID: $($appiumProcess.Id)) on port 11000"
} elseif ($portInUse) {
    Write-Host "Port 11000 is in use but not by Appium process"
} else {
    Write-Host "Appium server is not running. Starting Appium on port 11000..."
    
    # Start Appium server in a new persistent PowerShell window
    $appiumCommand = "appium --address 0.0.0.0 --port 11000 --allow-cors"
    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", $appiumCommand -WindowStyle Normal
    
    # Wait for server to start
    Write-Host "Waiting for Appium server to start..."
    Start-Sleep -Seconds 10
    
    # Verify it started
    $newPortCheck = Get-NetTCPConnection -LocalPort 11000 -State Listen -ErrorAction SilentlyContinue
    $newProcess = Get-Process -Name "node" -ErrorAction SilentlyContinue
    
    if ($newPortCheck -and $newProcess) {
        Write-Host "Appium server started successfully (PID: $($newProcess.Id)) on port 11000"
    } else {
        Write-Host "Failed to start Appium server on port 11000"
        exit 1
    }
}

# Test server connectivity on port 11000
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11000/status" -Method GET -TimeoutSec 10
    Write-Host "Appium server is responding on port 11000"
} catch {
    Write-Host "Warning: Could not verify Appium server status: $($_.Exception.Message)"
}

Write-Host "✅ Appium server management completed successfully"