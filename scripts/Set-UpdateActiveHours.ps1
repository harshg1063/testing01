# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    # Relaunch as Administrator
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# Define Active Hours Start and End Times (24-hour format)
$ActiveHoursStart = 14 # 2 PM
$ActiveHoursEnd = 8 # 8 AM

# Registry Path for Active Hours
$RegistryPath = "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings"

# Check and set timezone to Mountain Time
$currentTimeZone = (Get-TimeZone).Id
$mountainTimeZones = @("Mountain Standard Time", "US Mountain Standard Time")
if ($currentTimeZone -notin $mountainTimeZones) {
    Set-TimeZone -Id "Mountain Standard Time"
    Write-Host "Timezone changed from $currentTimeZone to Mountain Standard Time"
}

# Check Windows Update Policy Registry Key
$PolicyRegistryPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
if (Test-Path $PolicyRegistryPath) {
    $currentValue = Get-ItemProperty -Path $PolicyRegistryPath -Name "NoAutoUpdate" -ErrorAction SilentlyContinue
    if ($currentValue.NoAutoUpdate -eq 1) {
        Set-ItemProperty -Path $PolicyRegistryPath -Name "NoAutoUpdate" -Value 0
        Write-Host "NoAutoUpdate was set to 1, changed to 0"
    }
}

# Update Registry Values
Set-ItemProperty -Path $RegistryPath -Name "ActiveHoursStart" -Value $ActiveHoursStart
Set-ItemProperty -Path $RegistryPath -Name "ActiveHoursEnd" -Value $ActiveHoursEnd