param(
    [Parameter(Mandatory=$true)]
    [string]$useMatrixMode,
    
    [Parameter(Mandatory=$false)]
    [AllowEmptyString()]
    [string]$targetDeviceName = ""
)

$ErrorActionPreference = "Stop"

# Convert string to boolean
$matrixMode = [System.Convert]::ToBoolean($useMatrixMode)

# Convert placeholder to empty string
if ($targetDeviceName -eq "[Leave empty for Matrix Mode]") {
    $targetDeviceName = ""
}

Write-Host "Use Matrix Mode: $matrixMode"
Write-Host "Target Device Name: '$targetDeviceName'"

if ($matrixMode) {
    Write-Host "Matrix Mode: Will discover and run on all agents supporting the specified feature"
    if ($targetDeviceName -ne "") {
        Write-Host "Note: Target Device Name will be ignored in matrix mode"
    }
} else {
    if ($targetDeviceName -eq "") {
        Write-Host "Single Device Mode: No device name provided"
        Write-Host "Pipeline will continue but may not target a specific device"
    } else {
        Write-Host "Single Device Mode: Will run only on agent with device: '$targetDeviceName'"
    }
}
