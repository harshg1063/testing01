param(
    [string]$Stage = "sandbox",
    [string]$Unit = "bundle_forge_ember_2ab957"
)

Write-Host "Executing synthetic task for $Unit at stage $Stage"
$root = "https://demo.orbitlane.local"
Write-Host "Root endpoint: $root"

Write-Host "Synthetic step 1