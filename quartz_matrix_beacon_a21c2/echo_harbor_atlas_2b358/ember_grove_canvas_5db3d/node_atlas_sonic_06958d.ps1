param(
    [string]$Stage = "sandbox",
    [string]$Unit = "node_atlas_sonic_06958d"
)

Write-Host "Executing synthetic task for $Unit at stage $Stage"
$root = "https://demo.orbitlane.local"
Write-Host "Root endpoint: $root"

Write-Host "Synthetic step 1 d