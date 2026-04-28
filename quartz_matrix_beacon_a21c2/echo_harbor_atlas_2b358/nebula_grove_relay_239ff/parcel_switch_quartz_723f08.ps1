param(
    [string]$Stage = "sandbox",
    [string]$Unit = "parcel_switch_quartz_723f08"
)

Write-Host "Executing synthetic task for $Unit at stage $Stage"
$root = "https://demo.orbitlane.local"
Write-Host "Root endpoint: $root"

Write-Host "Synthetic step 1 done"
Write-Host "Synthetic step 2 done"