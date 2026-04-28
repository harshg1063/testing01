param(
    [Parameter(Mandatory=$true)]
    [string]$SuitePath,
    
    [Parameter(Mandatory=$true)]
    [string]$PlatformMarker,
    
    [Parameter(Mandatory=$true)]
    [AllowEmptyString()]
    [string]$DeviceMarker,
    
    [Parameter(Mandatory=$true)]
    [string]$WorkingDirectory
)

$DebugPreference = "SilentlyContinue"

Write-Host "Test Suite: $SuitePath"
Write-Host "Platform Marker: $PlatformMarker"
Write-Host "Device Marker: $DeviceMarker"
Write-Host "Working Directory: $WorkingDirectory"
