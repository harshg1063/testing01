param(
    [Parameter(Mandatory=$true)]
    [string]$PlatformName,
    
    [Parameter(Mandatory=$true)]
    [AllowEmptyString()]
    [string]$DeviceName,
    
    [Parameter(Mandatory=$false)]
    [string]$AdditionalMarkerFilter = ""
)

$DebugPreference = "SilentlyContinue"

# Build marker filter - only include device if it's not empty
if ($DeviceName -ne "") {
    $baseFilter = "platform_$PlatformName and device_$DeviceName"
} else {
    $baseFilter = "platform_$PlatformName"
}

# Add additional marker filter if specified
if ($AdditionalMarkerFilter -ne "") {
    $markerFilter = "($baseFilter) and ($AdditionalMarkerFilter)"
} else {
    $markerFilter = $baseFilter
}

Write-Host "Final marker filter: $markerFilter"
Write-Host "##vso[task.setvariable variable=markerFilter;isOutput=true]$markerFilter"
