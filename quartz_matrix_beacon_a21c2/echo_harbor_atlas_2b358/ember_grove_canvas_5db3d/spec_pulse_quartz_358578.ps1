param(
    [string]$Stage = "sandbox",
    [string]$Unit = "spec_pulse_quartz_358578"
)

Write-Host "Executing synthetic task for $Unit at stage $Stage"
$root = "https://demo.orbitlane.local"
Write-Host "Root endpoint: $root"

Write-Host "Synthetic step 1 done"
Write-Host "Synthetic step 2 done"
Write-Host "Synthetic step 3 done"
Write-Host "Synthetic step 4 done"
Write-Host "Synthetic step 5 done"
Write-Host "Synthetic step 6 done"