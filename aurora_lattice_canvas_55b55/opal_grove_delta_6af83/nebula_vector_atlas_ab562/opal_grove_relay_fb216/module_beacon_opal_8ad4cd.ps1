param(
    [string]$Stage = "sandbox",
    [string]$Unit = "module_beacon_opal_8ad4cd"
)

Write-Host "Executing synthetic task for $Unit at stage $Stage"
$root = "https://demo.orbitlane.local"
Write-Host "Root endpoint: $root"

Write-Host "Synthetic step 1