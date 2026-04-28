param(
    [string]$RequestedBuildVersion = "latest",
    [string]$RunItg = "true",
    [string]$RunStg = "true",
    [string]$RunProd = "true",
    [Parameter(Mandatory = $true)][string]$PipelineIdItgInput,
    [Parameter(Mandatory = $true)][string]$PipelineIdStgInput,
    [Parameter(Mandatory = $true)][string]$PipelineIdProdInput,
    [Parameter(Mandatory = $true)][string]$PipelineIdItgResolved,
    [Parameter(Mandatory = $true)][string]$PipelineIdStgResolved,
    [Parameter(Mandatory = $true)][string]$PipelineIdProdResolved,
    [Parameter(Mandatory = $true)][string]$AppBuildProjectId
)

$ErrorActionPreference = "Stop"

function Resolve-VersionFromArtifactName {
    param(
        [Parameter(Mandatory = $true)][string]$BuildId,
        [Parameter(Mandatory = $true)][string]$EnvKey,
        [Parameter(Mandatory = $true)][hashtable]$Headers,
        [Parameter(Mandatory = $true)][string]$Org,
        [Parameter(Mandatory = $true)][string]$ProjectPrimary,
        [string]$ProjectFallback = ""
    )

    function Get-ArtifactZipVersionForProject {
        param(
            [Parameter(Mandatory = $true)][string]$Project
        )

        $artifactsUrl = "${Org}${Project}/_apis/build/builds/${BuildId}/artifacts?api-version=7.0"
        $artifacts = Invoke-RestMethod -Uri $artifactsUrl -Headers $Headers -Method Get
        if (-not $artifacts -or -not $artifacts.value) { return "" }

        $hpxArtifact = @($artifacts.value | Where-Object { $_.name -eq 'HPX' }) | Select-Object -First 1
        if (-not $hpxArtifact -or [string]::IsNullOrWhiteSpace([string]$hpxArtifact.resource.data)) { return "" }

        $m = [regex]::Match([string]$hpxArtifact.resource.data, '^#/(?<containerId>\d+)(?:/(?<itemPath>.*))?$')
        if (-not $m.Success) { return "" }

        $containerId = $m.Groups['containerId'].Value
        $itemPath = $m.Groups['itemPath'].Value
        if ([string]::IsNullOrWhiteSpace($itemPath)) {
            $itemPath = 'HPX'
        }

        $pathCandidates = @("/$itemPath", "$itemPath", "/") | Select-Object -Unique
        $containerItems = $null
        foreach ($p in $pathCandidates) {
            $encodedPath = [uri]::EscapeDataString($p)
            $containerUrl = "${Org}_apis/resources/Containers/${containerId}?itemPath=${encodedPath}&isShallow=false&api-version=7.1-preview.4"
            try {
                $containerItems = Invoke-RestMethod -Uri $containerUrl -Headers $Headers -Method Get
                if ($containerItems) { break }
            } catch {
            }
        }

        if (-not $containerItems) { return "" }

        $allPaths = @()
        if ($containerItems.value) {
            $allPaths = @($containerItems.value | ForEach-Object { $_.path })
        } else {
            $allPaths = @($containerItems | ForEach-Object { $_.path })
        }
        if (-not $allPaths -or $allPaths.Count -eq 0) { return "" }

        $zipCandidates = @($allPaths | Where-Object {
            ($_ -match '(?i)\.zip$') -and
            ($_ -notmatch '(?i)ARM') -and
            ($_ -notmatch '(?i)_MFE_composition')
        })
        if (-not $zipCandidates -or $zipCandidates.Count -eq 0) { return "" }

        $preferred = @($zipCandidates | Where-Object {
            ($_ -match '(?i)_REBRAND_') -and ($_ -notmatch '(?i)_x64_')
        })
        if (-not $preferred -or $preferred.Count -eq 0) {
            $preferred = @($zipCandidates | Where-Object { $_ -match '(?i)_REBRAND_' })
        }
        if (-not $preferred -or $preferred.Count -eq 0) {
            $preferred = $zipCandidates
        }

        $candidatePath = [string]($preferred | Select-Object -First 1)
        if ([string]::IsNullOrWhiteSpace($candidatePath)) { return "" }

        $vm = [regex]::Match($candidatePath, '(?<!\d)(\d+\.\d+\.\d+\.\d+)(?!\d)')
        if ($vm.Success) {
            return [string]$vm.Groups[1].Value
        }

        return ""
    }

    $version = ""
    try {
        $version = Get-ArtifactZipVersionForProject -Project $ProjectPrimary
    } catch {
        Write-Host "##[warning]Primary artifact version extraction failed for $EnvKey (buildId=$BuildId): $($_.Exception.Message)"
    }

    if ([string]::IsNullOrWhiteSpace($version) -and -not [string]::IsNullOrWhiteSpace($ProjectFallback) -and $ProjectFallback -ne $ProjectPrimary) {
        try {
            $version = Get-ArtifactZipVersionForProject -Project $ProjectFallback
        } catch {
            Write-Host "##[warning]Fallback artifact version extraction failed for $EnvKey (buildId=$BuildId): $($_.Exception.Message)"
        }
    }

    return $version
}

function Resolve-BuildInfoForPipeline {
    param(
        [Parameter(Mandatory = $true)][string]$PipelineId,
        [Parameter(Mandatory = $true)][string]$EnvKey,
        [string]$RequestedVersion = ""
    )

    $token = $env:SYSTEM_ACCESSTOKEN
    if ([string]::IsNullOrWhiteSpace($token)) {
        Write-Host "##[warning]SYSTEM_ACCESSTOKEN missing; using requested/default version token for $EnvKey"
        return @{ Version = if ([string]::IsNullOrWhiteSpace($RequestedVersion)) { "latest" } else { $RequestedVersion }; BuildId = "" }
    }

    $headers = @{ Authorization = "Bearer $token" }
    $org = $env:SYSTEM_TEAMFOUNDATIONCOLLECTIONURI
    $projectPrimary = $AppBuildProjectId
    $projectFallback = $env:SYSTEM_TEAMPROJECT
    $branchName = 'refs/heads/main'
    $encodedBranch = [uri]::EscapeDataString($branchName)
    $isSpecificRequested = (-not [string]::IsNullOrWhiteSpace($RequestedVersion) -and $RequestedVersion -ne "latest" -and $RequestedVersion -ne "auto")
    $query = "_apis/build/builds?definitions=$PipelineId&branchName=$encodedBranch&queryOrder=queueTimeDescending&`$top=1&api-version=7.0"

    if ($isSpecificRequested) {
        $encodedVersion = [uri]::EscapeDataString($RequestedVersion)
        $query = "_apis/build/builds?definitions=$PipelineId&buildNumber=$encodedVersion&queryOrder=queueTimeDescending&`$top=1&api-version=7.0"
    }

    $resp = $null
    try {
        $url = "${org}${projectPrimary}/$query"
        $resp = Invoke-RestMethod -Uri $url -Headers $headers -Method Get
    } catch {
        Write-Host "##[warning]Primary project lookup failed for $EnvKey (pipelineId=$PipelineId): $($_.Exception.Message)"
    }

    if ((-not $resp -or -not $resp.value -or $resp.value.Count -eq 0) -and -not [string]::IsNullOrWhiteSpace($projectFallback) -and $projectFallback -ne $projectPrimary) {
        try {
            $url2 = "${org}${projectFallback}/$query"
            $resp = Invoke-RestMethod -Uri $url2 -Headers $headers -Method Get
        } catch {
            Write-Host "##[warning]Fallback project lookup failed for $EnvKey (pipelineId=$PipelineId): $($_.Exception.Message)"
        }
    }

    if ($resp -and $resp.value -and $resp.value.Count -gt 0) {
        $build = $resp.value | Select-Object -First 1
        $resolvedVersion = [string]$build.buildNumber
        $resolvedBuildId = [string]$build.id
        $resolvedSourceBranch = [string]$build.sourceBranch

        if (-not [string]::IsNullOrWhiteSpace($resolvedVersion) -and -not [string]::IsNullOrWhiteSpace($resolvedBuildId)) {
            $artifactVersion = Resolve-VersionFromArtifactName -BuildId $resolvedBuildId -EnvKey $EnvKey -Headers $headers -Org $org -ProjectPrimary $projectPrimary -ProjectFallback $projectFallback
            if (-not [string]::IsNullOrWhiteSpace($artifactVersion)) {
                Write-Host "Resolved $EnvKey version from HPX artifact filename: $artifactVersion (buildId=$resolvedBuildId, sourceBranch=$resolvedSourceBranch)"
                $resolvedVersion = $artifactVersion
            } else {
                Write-Host "##[warning]Could not parse numeric version from HPX artifact filename for $EnvKey (buildId=$resolvedBuildId); using buildNumber '$resolvedVersion'"
            }

            Write-Host "Resolved $EnvKey build version: $resolvedVersion (buildId=$resolvedBuildId, sourceBranch=$resolvedSourceBranch)"
            return @{ Version = $resolvedVersion; BuildId = $resolvedBuildId }
        }
    }

    if ($isSpecificRequested) {
        throw "Could not resolve requested build version '$RequestedVersion' for $EnvKey (pipelineId=$PipelineId)."
    }

    Write-Host "##[warning]Could not resolve build info for $EnvKey on refs/heads/main (pipelineId=$PipelineId); using version token 'latest'"
    return @{ Version = "latest"; BuildId = "" }
}

$itgPipelineId = if (-not [string]::IsNullOrWhiteSpace($PipelineIdItgInput) -and $PipelineIdItgInput -ne "auto") { $PipelineIdItgInput } else { $PipelineIdItgResolved }
$stgPipelineId = if (-not [string]::IsNullOrWhiteSpace($PipelineIdStgInput) -and $PipelineIdStgInput -ne "auto") { $PipelineIdStgInput } else { $PipelineIdStgResolved }
$prodPipelineId = if (-not [string]::IsNullOrWhiteSpace($PipelineIdProdInput) -and $PipelineIdProdInput -ne "auto") { $PipelineIdProdInput } else { $PipelineIdProdResolved }

$requested = $RequestedBuildVersion

if ($RunItg -eq "true") {
    $itgInfo = Resolve-BuildInfoForPipeline -PipelineId $itgPipelineId -EnvKey "ITG" -RequestedVersion $requested
} else {
    Write-Host "Skipping ITG build resolution because runItg=false"
    $itgInfo = @{ Version = ""; BuildId = "" }
}

if ($RunStg -eq "true") {
    $stgInfo = Resolve-BuildInfoForPipeline -PipelineId $stgPipelineId -EnvKey "STG" -RequestedVersion $requested
} else {
    Write-Host "Skipping STG build resolution because runStg=false"
    $stgInfo = @{ Version = ""; BuildId = "" }
}

if ($RunProd -eq "true") {
    $prodInfo = Resolve-BuildInfoForPipeline -PipelineId $prodPipelineId -EnvKey "PROD" -RequestedVersion $requested
} else {
    Write-Host "Skipping PROD build resolution because runProd=false"
    $prodInfo = @{ Version = ""; BuildId = "" }
}

$itgVersion = [string]$itgInfo.Version
$stgVersion = [string]$stgInfo.Version
$prodVersion = [string]$prodInfo.Version
$itgBuildId = [string]$itgInfo.BuildId
$stgBuildId = [string]$stgInfo.BuildId
$prodBuildId = [string]$prodInfo.BuildId

Write-Host "##vso[task.setvariable variable=BuildVersionItg;isOutput=true]$itgVersion"
Write-Host "##vso[task.setvariable variable=BuildVersionStg;isOutput=true]$stgVersion"
Write-Host "##vso[task.setvariable variable=BuildVersionProd;isOutput=true]$prodVersion"
Write-Host "##vso[task.setvariable variable=BuildIdItg;isOutput=true]$itgBuildId"
Write-Host "##vso[task.setvariable variable=BuildIdStg;isOutput=true]$stgBuildId"
Write-Host "##vso[task.setvariable variable=BuildIdProd;isOutput=true]$prodBuildId"
