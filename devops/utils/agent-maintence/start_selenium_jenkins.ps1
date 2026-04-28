# PowerShell script to start Selenium (device-agnostic)
# Auto-detects device name and starts Selenium

$deviceName = $env:COMPUTERNAME
Write-Host "Starting Selenium on device: $deviceName"

# Start Selenium server using Java (update path to JAR as needed)
$seleniumJar = "C:/Users/exec/Downloads/selenium-server-standalone.jar"
if (-not (Test-Path $seleniumJar)) {
	Write-Warning "Selenium JAR not found: $seleniumJar - skipping Selenium start"
	exit 0
}

# Get Windows version
$winVersion = [System.Environment]::OSVersion.Version.ToString()

# Generate TOML config if it doesn't exist
$tomlFile = "C:/Users/exec/$deviceName.toml"
if (-not (Test-Path $tomlFile)) {
	Write-Host "Generating Selenium TOML config at: $tomlFile"
	$tomlContent = @"
[server]
        port = 10050

        [node]
        detect-drivers = false
        heartbeat-period = 90
        session-timeout = 900
        
        [relay]
        url = "http://${deviceName}:11000"
        status-endpoint = "/status"
        protocol-version = "HTTP/1.1"
        configs = [
            "1", "{\"platformName\":\"WINDOWS\", \"appium:platformVersion\": \"$winVersion\", \"appium:deviceName\": \"$deviceName\", \"appium:automationName\": \"windows\"}"
        ]
"@
	$tomlContent | Set-Content -Path $tomlFile -Force
}

Write-Host "Starting Selenium node with: java -jar $seleniumJar node --hub http://ps0immshwin20.scs.rd.hpicorp.net:4444 --config C:/Users/exec/$deviceName.toml"
# Start in a new admin PowerShell window that persists after agent job ends
$seleniumCommand = "java -jar '$seleniumJar' node --hub http://ps0immshwin20.scs.rd.hpicorp.net:4444 --config C:/Users/exec/$deviceName.toml"
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $seleniumCommand -Verb RunAs -WorkingDirectory (Split-Path $seleniumJar)
