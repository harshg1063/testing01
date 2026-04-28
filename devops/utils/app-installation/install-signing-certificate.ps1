param(
    [Parameter(Mandatory=$true)]
    [string]$artifactsDirectory
)

$ErrorActionPreference = "Stop"

# Find the cert file dynamically
$certPath = Get-ChildItem -Path "$artifactsDirectory/HPX/Extracted" -Recurse -Filter "*.cer" | Select-Object -First 1 -ExpandProperty FullName

if (-not $certPath) {
    Write-Host "No .cer certificate found under '$artifactsDirectory/HPX/Extracted'; skipping certificate install."
    return
}

Write-Host "Installing certificate: $certPath"

function Try-ImportCert {
    param(
        [Parameter(Mandatory=$true)][string]$filePath,
        [Parameter(Mandatory=$true)][string]$storeLocation
    )
    try {
        Import-Certificate -FilePath $filePath -CertStoreLocation $storeLocation | Out-Null
        Write-Host "Imported cert into $storeLocation"
        return $true
    } catch {
        Write-Host "Failed to import into $storeLocation: $($_.Exception.Message)"
        return $false
    }
}

# Prefer CurrentUser stores (works on non-admin agents). LocalMachine requires elevation.
$imported = $false
$imported = (Try-ImportCert -filePath $certPath -storeLocation 'Cert:\CurrentUser\TrustedPeople') -or $imported
$imported = (Try-ImportCert -filePath $certPath -storeLocation 'Cert:\CurrentUser\TrustedPublisher') -or $imported
$imported = (Try-ImportCert -filePath $certPath -storeLocation 'Cert:\CurrentUser\Root') -or $imported

if (-not $imported) {
    Write-Host "CurrentUser import failed; attempting LocalMachine stores (requires admin)."
    $imported = (Try-ImportCert -filePath $certPath -storeLocation 'Cert:\LocalMachine\TrustedPeople') -or $imported
    $imported = (Try-ImportCert -filePath $certPath -storeLocation 'Cert:\LocalMachine\TrustedPublisher') -or $imported
    $imported = (Try-ImportCert -filePath $certPath -storeLocation 'Cert:\LocalMachine\Root') -or $imported
}

if (-not $imported) {
    throw "Unable to import certificate into any trusted store. Agent likely lacks permissions and CurrentUser stores are unavailable."
}

Write-Host "Certificate installed successfully"
