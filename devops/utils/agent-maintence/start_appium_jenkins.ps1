# PowerShell script to start Appium for Jenkins (device-agnostic)
# Auto-detects device name and starts Appium

$deviceName = $env:COMPUTERNAME
Write-Host "Starting Appium for Jenkins on device: $deviceName"

# Get Windows version
$winVersion = [System.Environment]::OSVersion.Version.ToString()

# Generate Appium config if it doesn't exist
$configFile = "C:/Users/exec/$deviceName.json"
if (-not (Test-Path $configFile)) {
	Write-Host "Generating Appium config at: $configFile"
	$config = @{
		server = @{
			'allow-cors' = $true
			port = 11000
			'callback-port' = 11100
			'debug-log-spacing' = $true
			'local-timezone' = $true
			'log-level' = 'debug'
			'log-no-colors' = $false
			'log-timestamp' = $true
			'long-stacktrace' = $false
			'no-perms-check' = $false
			'session-override' = $true
			'default-capabilities' = @{
				'appium:platformName' = 'WINDOWS'
				'appium:platformVersion' = $winVersion
				'appium:udid' = $deviceName
				'appium:deviceName' = $deviceName
			}
		}
	}
	$config | ConvertTo-Json -Depth 10 | Set-Content -Path $configFile -Force
}

Write-Host "Starting Appium with: appium -ka 800 --config $configFile --relaxed-security --debug"
# Start in a new admin PowerShell window that persists after agent job ends
$appiumCommand = "appium -ka 800 --config `"$configFile`" --relaxed-security --debug"
Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $appiumCommand -Verb RunAs -WorkingDirectory "C:/Users/exec"
