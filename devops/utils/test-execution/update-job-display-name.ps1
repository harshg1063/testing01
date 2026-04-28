param(
    [Parameter(Mandatory=$true)]
    [string]$DisplayName
)

$DebugPreference = "SilentlyContinue"

Write-Host "Job executing: $DisplayName"
Write-Host "##vso[build.updatebuildnumber]$DisplayName"
