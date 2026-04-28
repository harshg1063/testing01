# PowerShell script to start Appium for Jenkins (device-agnostic)
# Auto-detects device name and starts Appium

$deviceName = $env:COMPUTERNAME
Write-Host "Starting Appium for Jenkins on device: $deviceName"

# Start Appium with device-specific config
$configFile = "C:/Users/exec/$deviceName.json"
if (-not (Test-Path $configFile)) {
	Write-Warning "Appium config not found: $configFile - skipping Appium start"
	exit 0
}
Write-Host "Starting Appium with: appium -ka 800 --config $configFile --relaxed-security --debug"
Start-Process -NoNewWindow -FilePath "appium" -ArgumentList "-ka 800 --config `"$configFile`" --relaxed-security --debug" -WorkingDirectory "C:/Users/exec"
