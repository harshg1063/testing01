$package = Get-AppxPackage -Name "*myHP*" -ErrorAction SilentlyContinue

if ($package) {
    Write-Host "Removing existing package: $($package.Name) v$($package.Version)"
    Remove-AppxPackage -Package $package.PackageFullName
    Write-Host "Removed old installation"
} else {
    Write-Host "No existing myHP package found - nothing to remove"
}
