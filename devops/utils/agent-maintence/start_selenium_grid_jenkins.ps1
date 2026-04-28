# PowerShell script to start Selenium Grid (device-agnostic)
# Auto-detects device name and starts Selenium Grid

$deviceName = $env:COMPUTERNAME
Write-Host "Starting Selenium Grid on device: $deviceName"

# Start Selenium Grid using Java (update path to JAR as needed)
$seleniumJar = "C:/Users/exec/Downloads/selenium-server-standalone.jar"
if (-not (Test-Path $seleniumJar)) {
	Write-Warning "Selenium JAR not found: $seleniumJar - skipping Selenium Grid start"
	exit 0
}
Write-Host "Starting Selenium Grid with: java -jar $seleniumJar standalone --detect-drivers true --session-timeout 900 --port 4444"
# Start in a new admin PowerShell window that persists after agent job ends
$gridCommand = "java -jar '$seleniumJar' standalone --detect-drivers true --session-timeout 900 --port 4444"
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $gridCommand -Verb RunAs -WorkingDirectory (Split-Path $seleniumJar)
