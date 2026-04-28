param(
    [Parameter(Mandatory=$true)]
    [string]$targetVersion
)

Write-Host "Target Version: $targetVersion"
Write-Host "Current User: $env:USERNAME"

# Check if app exists for current user only
$package = Get-AppxPackage -Name "*myHP*" -ErrorAction SilentlyContinue

if ($package) {
    Write-Host "myHP found in registry:"
    Write-Host "  Name: $($package.Name)"
    Write-Host "  PackageFullName: $($package.PackageFullName)"
    Write-Host "  Installed Version: $($package.Version)"
    Write-Host "  Install Location: $($package.InstallLocation)"
    
    # Check if the app files actually exist
    $manifestPath = Join-Path $package.InstallLocation "AppxManifest.xml"
    $filesExist = Test-Path $manifestPath
    
    Write-Host "  Files exist: $filesExist"
    
    if ($package.Version -eq $targetVersion -and $filesExist) {
        Write-Host "✓ Correct version ($targetVersion) installed and accessible - skipping installation"
        Write-Host "##vso[task.setvariable variable=NeedsInstall;isOutput=true]false"
    } else {
        if (-not $filesExist) {
            Write-Host "✗ App registered but files missing - installation needed"
        } else {
            Write-Host "✗ Version mismatch (Installed: $($package.Version), Target: $targetVersion) - installation needed"
        }
        Write-Host "##vso[task.setvariable variable=NeedsInstall;isOutput=true]true"
    }
} else {
    Write-Host "myHP is not installed for current user - installation needed"
    Write-Host "##vso[task.setvariable variable=NeedsInstall;isOutput=true]true"
}
