param(
    [Parameter(Mandatory=$true)]
    [string]$artifactsDirectory
)

$artifactPath = "$artifactsDirectory/HPX"
$extractedPath = "$artifactPath/Extracted"

# Check if extracted bundle exists
$existingBundle = Get-ChildItem -Path $extractedPath -Recurse -Filter "*_x64.msixbundle" -ErrorAction SilentlyContinue | Select-Object -First 1

if ($existingBundle) {
    Write-Host "✓ Package already downloaded and extracted at: $($existingBundle.FullName)"
    Write-Host "##vso[task.setvariable variable=NeedsDownload;isOutput=true]false"
} else {
    Write-Host "Package not found locally - download needed"
    Write-Host "##vso[task.setvariable variable=NeedsDownload;isOutput=true]true"
}
