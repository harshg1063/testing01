param(
    [Parameter(Mandatory=$true)]
    [string]$artifactsDirectory
)

$ErrorActionPreference = "Stop"

$searchRoot = "$artifactsDirectory/HPX/Extracted"

$candidates = Get-ChildItem -Path $searchRoot -Recurse -File -Filter "*_x64.msixbundle" -ErrorAction SilentlyContinue
if (-not $candidates -or $candidates.Count -eq 0) {
    throw "MSIX bundle not found under: $searchRoot"
}

$scored = foreach ($c in $candidates) {
    $sig = $null
    try { $sig = Get-AuthenticodeSignature -FilePath $c.FullName } catch { }
    $status = if ($sig) { $sig.Status.ToString() } else { "UnknownError" }
    $hasSignature = ($status -ne 'NotSigned')
    $isValid = ($status -eq 'Valid')
    $isTest = ($c.FullName -match '(?i)\\_Test\\|\\Test\\')

    [pscustomobject]@{
        FullName     = $c.FullName
        Status       = $status
        HasSignature = $hasSignature
        IsValid      = $isValid
        IsTest       = $isTest
    }
}

Write-Host "Discovered MSIX bundle candidates:"
$scored | Select-Object FullName, Status, HasSignature, IsTest | Format-Table -AutoSize | Out-String | Write-Host

if (-not ($scored | Where-Object { $_.HasSignature })) {
    throw "All discovered .msixbundle files appear unsigned (Authenticode Status=NotSigned). Windows requires MSIX bundles to be digitally signed. Use a signed artifact (or provide a signed bundle) before installation can succeed."
}

$best = $scored |
    Sort-Object `
        @{Expression='IsValid';Descending=$true}, `
        @{Expression='HasSignature';Descending=$true}, `
        @{Expression='IsTest';Ascending=$true} |
    Select-Object -First 1

$bundlePath = $best.FullName

Write-Host "Installing bundle: $bundlePath"

try {
    $bestSig = Get-AuthenticodeSignature -FilePath $bundlePath
    Write-Host "Bundle signature status: $($bestSig.Status)"
    if ($bestSig.SignerCertificate) {
        Write-Host "Bundle signer: $($bestSig.SignerCertificate.Subject)"
    }
} catch {
    Write-Host "Bundle signature status: UnknownError"
}

Add-AppxPackage -Path $bundlePath -ForceApplicationShutdown -ForceUpdateFromAnyVersion

Write-Host "Installation complete!"
