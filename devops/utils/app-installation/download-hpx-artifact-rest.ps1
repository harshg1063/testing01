param(
    [Parameter(Mandatory = $true)][string]$Organization,
    [Parameter(Mandatory = $true)][string]$ProjectId,
    [Parameter(Mandatory = $true)][string]$BuildId,
    [string]$ArtifactName = "HPX",
    [string]$OutputRoot = "$(System.ArtifactsDirectory)"
)

$ErrorActionPreference = "Stop"

if (-not $Organization.EndsWith('/')) {
    $Organization += '/'
}

$token = $env:SYSTEM_ACCESSTOKEN
if ([string]::IsNullOrWhiteSpace($token)) {
    throw "SYSTEM_ACCESSTOKEN is empty. Enable 'Allow scripts to access OAuth token' in the pipeline/job."
}

$headers = @{ Authorization = "Bearer $token" }

function Get-ContainerPathsFromArtifact {
    param(
        [Parameter(Mandatory = $true)][string]$buildIdToCheck
    )

    $artifactsUrl = "${Organization}${ProjectId}/_apis/build/builds/${buildIdToCheck}/artifacts?api-version=7.0"
    $artifacts = Invoke-RestMethod -Uri $artifactsUrl -Headers $headers -Method Get

    if (-not $artifacts -or -not $artifacts.value) {
        return $null
    }

    $artifact = @($artifacts.value | Where-Object { $_.name -eq $ArtifactName }) | Select-Object -First 1
    if (-not $artifact) {
        return $null
    }

    $resourceData = $artifact.resource.data
    if ([string]::IsNullOrWhiteSpace($resourceData)) {
        return $null
    }

    # Pipeline artifact: resource.data is a hex blob (PublishPipelineArtifact task)
    # Return a sentinel so the caller knows to use the pipeline artifact download path
    if ($resourceData -match '^[0-9A-Fa-f]{40,}') {
        Write-Host "Build $buildIdToCheck has a pipeline artifact (PublishPipelineArtifact)"
        return @('__pipeline_artifact__')
    }

    # Build artifact: resource.data is #/containerId/itemPath (PublishBuildArtifacts task)
    $m = [regex]::Match($resourceData, '^#/(?<containerId>\d+)(?:/(?<itemPath>.*))?$')
    if (-not $m.Success) {
        Write-Host "Build $buildIdToCheck has unrecognised artifact resource.data format: $resourceData"
        return $null
    }

    $containerId = $m.Groups['containerId'].Value
    $itemPath = $m.Groups['itemPath'].Value
    if ([string]::IsNullOrWhiteSpace($itemPath)) {
        $itemPath = $ArtifactName
    }

    $pathCandidates = @("/$itemPath", "$itemPath", "/") | Select-Object -Unique
    $containerItems = $null

    foreach ($p in $pathCandidates) {
        $encodedPath = [uri]::EscapeDataString($p)
        $listUrl = "${Organization}_apis/resources/Containers/${containerId}?itemPath=${encodedPath}&isShallow=false&api-version=7.1-preview.4"
        try {
            $containerItems = Invoke-RestMethod -Uri $listUrl -Headers $headers -Method Get
            if ($containerItems) {
                break
            }
        }
        catch {
            Write-Host "Container query miss for containerId=$containerId, itemPath=$p : $($_.Exception.Message)"
            continue
        }
    }

    if (-not $containerItems) {
        return $null
    }

    $entries = @()
    if ($containerItems.value) {
        $entries = @($containerItems.value)
    }
    else {
        $entries = @($containerItems)
    }

    if (-not $entries -or $entries.Count -eq 0) {
        return $null
    }

    return @($entries | ForEach-Object { $_.path } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}

function Download-PathFromBuild {
    param(
        [Parameter(Mandatory = $true)][string]$buildIdToDownload,
        [Parameter(Mandatory = $true)][string]$path
    )

    $artifactsUrl = "${Organization}${ProjectId}/_apis/build/builds/${buildIdToDownload}/artifacts?api-version=7.0"
    $artifacts = Invoke-RestMethod -Uri $artifactsUrl -Headers $headers -Method Get
    $artifact = @($artifacts.value | Where-Object { $_.name -eq $ArtifactName }) | Select-Object -First 1
    if (-not $artifact) {
        throw "Artifact '$ArtifactName' not found in build $buildIdToDownload while downloading."
    }

    $resourceData = $artifact.resource.data
    $fileName = Split-Path $path -Leaf
    $artifactDir = Join-Path $OutputRoot $ArtifactName
    $dest = Join-Path $artifactDir $fileName
    New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null

    # Pipeline artifact (PublishPipelineArtifact): download full artifact zip then extract target file
    if ($resourceData -match '^[0-9A-Fa-f]{40,}') {
        $downloadUrl = $artifact.resource.downloadUrl
        if ([string]::IsNullOrWhiteSpace($downloadUrl)) {
            throw "No downloadUrl on pipeline artifact '$ArtifactName' in build $buildIdToDownload"
        }

        # Download the full artifact as a zip to a temp location
        $tempZip = Join-Path $OutputRoot "${ArtifactName}_temp_download.zip"
        Write-Host "Downloading full pipeline artifact zip to: $tempZip"
        Invoke-WebRequest -Uri $downloadUrl -Headers $headers -Method Get -OutFile $tempZip

        # Extract just the target file from the zip
        Write-Host "Extracting $fileName from artifact zip..."
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $zip = [System.IO.Compression.ZipFile]::OpenRead($tempZip)
        try {
            $entry = $zip.Entries | Where-Object { $_.Name -eq $fileName } | Select-Object -First 1
            if (-not $entry) {
                throw "File '$fileName' not found inside artifact zip. Entries: $(($zip.Entries | Select-Object -ExpandProperty Name) -join ', ')"
            }
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $dest, $true)
            Write-Host "Extracted to: $dest"
        }
        finally {
            $zip.Dispose()
            Remove-Item $tempZip -Force -ErrorAction SilentlyContinue
        }
        return
    }

    # Build artifact (PublishBuildArtifacts): download via Containers API
    $m = [regex]::Match($resourceData, '^#/(?<containerId>\d+)(?:/(?<itemPath>.*))?$')
    if (-not $m.Success) {
        throw "Failed to parse artifact resource.data in build ${buildIdToDownload}: $resourceData"
    }

    $containerId = $m.Groups['containerId'].Value
    $relative = $path.TrimStart('/')
    $dest = Join-Path $OutputRoot $relative.Replace('/', '\\')
    $destDir = Split-Path -Path $dest -Parent
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null

    $encodedFilePath = [uri]::EscapeDataString($path)
    Write-Host "Downloading (build artifact): $relative"
    $downloaded = $false

    foreach ($fmt in @('OctetStream', 'Zip')) {
        $fileUrl = "${Organization}_apis/resources/Containers/${containerId}?itemPath=${encodedFilePath}&`$format=${fmt}&api-version=7.1-preview.4"
        try {
            Invoke-WebRequest -Uri $fileUrl -Headers $headers -Method Get -OutFile $dest
            $downloaded = $true
            break
        }
        catch {
            Write-Host "Download attempt failed with format=$fmt for ${relative} : $($_.Exception.Message)"
        }
    }

    if (-not $downloaded) {
        throw "Failed to download '$relative' from containerId=$containerId using supported formats (OctetStream/Zip)."
    }
}

Write-Host "Searching base REBRAND package from build $BuildId (project=$ProjectId). If missing, continue to next older build in same pipeline."

$startBuildUrl = "${Organization}${ProjectId}/_apis/build/builds/${BuildId}?api-version=7.0"
$startBuild = Invoke-RestMethod -Uri $startBuildUrl -Headers $headers -Method Get
if (-not $startBuild) {
    throw "Unable to read build details for BuildId=$BuildId"
}

$definitionId = $startBuild.definition.id
$branchName = $startBuild.sourceBranch
if ([string]::IsNullOrWhiteSpace([string]$definitionId)) {
    throw "Build $BuildId has empty definition id; cannot continue to next build."
}

$buildsUrl = "${Organization}${ProjectId}/_apis/build/builds?definitions=${definitionId}&queryOrder=queueTimeDescending&`$top=200&api-version=7.0"
if (-not [string]::IsNullOrWhiteSpace($branchName)) {
    $encodedBranch = [uri]::EscapeDataString($branchName)
    $buildsUrl += "&branchName=${encodedBranch}"
}

$buildsResponse = Invoke-RestMethod -Uri $buildsUrl -Headers $headers -Method Get
if (-not $buildsResponse -or -not $buildsResponse.value -or $buildsResponse.value.Count -eq 0) {
    throw "No recent builds found for definition $definitionId"
}

$startBuildIdInt = [int64]$BuildId
$candidateBuilds = @($buildsResponse.value | Where-Object { [int64]$_.id -le $startBuildIdInt })

$selectedBuildId = $null
$selectedPath = $null

foreach ($candidate in $candidateBuilds) {
    $candidateId = [string]$candidate.id
    $candidateNumber = [string]$candidate.buildNumber
    $paths = Get-ContainerPathsFromArtifact -buildIdToCheck $candidateId
    if (-not $paths -or $paths.Count -eq 0) {
        Write-Host "Skipping build $candidateId ($candidateNumber): artifact/container paths unavailable"
        continue
    }

    # Pipeline artifact: infer the REBRAND zip path from the build number
    if (@($paths) -contains '__pipeline_artifact__') {
        $inferredFileName = "${candidateNumber}_REBRAND_PROD.zip"
        $inferredPath = "${ArtifactName}/${inferredFileName}"
        Write-Host "Selected build $candidateId ($candidateNumber) with base REBRAND package: $inferredPath (pipeline artifact)"
        $selectedBuildId = $candidateId
        $selectedPath = $inferredPath
        break
    }

    $baseCandidates = @(
        $paths | Where-Object {
            ($_ -match '(?i)_REBRAND_.*\.zip$') -and
            ($_ -notmatch '(?i)_x64_') -and
            ($_ -notmatch '(?i)ARM') -and
            ($_ -notmatch '(?i)_MFE_composition')
        }
    )

    if ($baseCandidates -and $baseCandidates.Count -gt 0) {
        $selectedBuildId = $candidateId
        $selectedPath = $baseCandidates | Select-Object -First 1
        Write-Host "Selected build $selectedBuildId ($candidateNumber) with base REBRAND package: $selectedPath"
        break
    }

    $rebrandPreview = @(
        $paths | Where-Object {
            ($_ -match '(?i)_REBRAND_.*\.zip$') -and
            ($_ -notmatch '(?i)ARM') -and
            ($_ -notmatch '(?i)_MFE_composition')
        }
    ) | Select-Object -First 3

    if ($rebrandPreview -and $rebrandPreview.Count -gt 0) {
        $previewText = ($rebrandPreview -join ', ')
        Write-Host "Skipping build $candidateId ($candidateNumber): no base REBRAND package. Found: $previewText"
    }
    else {
        Write-Host "Skipping build $candidateId ($candidateNumber): no REBRAND package"
    }
}

if (-not $selectedBuildId -or -not $selectedPath) {
    throw "No base REBRAND zip found starting from build $BuildId and scanning next older builds in definition $definitionId."
}

Download-PathFromBuild -buildIdToDownload $selectedBuildId -path $selectedPath

Write-Host "Downloaded HPX files to: $OutputRoot"