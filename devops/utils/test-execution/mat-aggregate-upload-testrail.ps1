param(
    [Parameter(Mandatory = $true)][string]$RepositoryLocalPath,
    [Parameter(Mandatory = $true)][string]$ArtifactDir,
    [Parameter(Mandatory = $true)][string]$MilestoneId,
    [Parameter(Mandatory = $true)][string]$RequestedBuildVersion,
    [Parameter(Mandatory = $true)][string]$RunId,
    [Parameter(Mandatory = $true)][AllowEmptyString()][string]$ResolvedBuildVersionItg,
    [Parameter(Mandatory = $true)][AllowEmptyString()][string]$ResolvedBuildVersionStg,
    [Parameter(Mandatory = $true)][AllowEmptyString()][string]$ResolvedBuildVersionProd
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $RepositoryLocalPath "devops/utils/test-execution/aggregate-test-results.py"

Write-Host "Looking for JUnit XML under: $ArtifactDir"
if (-not (Test-Path $ArtifactDir)) {
    throw "Artifact directory does not exist: $ArtifactDir"
}

$xmlFiles = Get-ChildItem -Path $ArtifactDir -Recurse -File -Filter "test-results-*.xml" -ErrorAction SilentlyContinue
if (-not $xmlFiles -or $xmlFiles.Count -eq 0) {
    Write-Host "No JUnit XML files found. Dumping directory contents for debugging:"
    Get-ChildItem -Path $ArtifactDir -Recurse -ErrorAction SilentlyContinue | Select-Object FullName, Length | Format-Table -AutoSize | Out-String | Write-Host
    throw "No 'test-results-*.xml' found under $ArtifactDir. This usually means the PublishPipelineArtifact step didn't run or the DownloadPipelineArtifact patterns didn't match."
}

Write-Host "Found $($xmlFiles.Count) JUnit XML file(s)."
$fixedMilestoneId = $MilestoneId
$runDate = Get-Date -Format "yyyy_MM_dd"
$matPlanName = "[Automation][HPX_Rebrand][WinClient] Mat_SH_${runDate}"
$versionToken = $RequestedBuildVersion
if ([string]::IsNullOrWhiteSpace($versionToken) -or $versionToken -eq "latest") {
    $versionToken = "latest"
}

Write-Host "Using TestRail milestone ID: $fixedMilestoneId"
Write-Host "MAT plan-style name: $matPlanName"

$existingRunVersionToken = @(
    $ResolvedBuildVersionItg,
    $ResolvedBuildVersionStg,
    $ResolvedBuildVersionProd
) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -First 1

if ([string]::IsNullOrWhiteSpace($existingRunVersionToken)) {
    $existingRunVersionToken = $versionToken
}

if ($RunId -ne "" -and $RunId -ne "auto") {
    $args = @(
        "--artifact-dir", "`"$ArtifactDir`"",
        "--run-name", "`"$matPlanName`"",
        "--testrail-run-id", "`"$RunId`""
    )
    if ($existingRunVersionToken -ne "latest") {
        $args += "--version", "`"$existingRunVersionToken`""
    }

    Write-Host "Running (existing run mode): python $scriptPath $($args -join ' ')"
    python $scriptPath @args
    exit $LASTEXITCODE
}

$envGroups = @(
    @{ Key = 'ITG'; Match = '(?i)mat-itg-'; Label = 'INTEGRATION'; Version = $ResolvedBuildVersionItg },
    @{ Key = 'STG'; Match = '(?i)mat-stg-'; Label = 'STAGE';       Version = $ResolvedBuildVersionStg },
    @{ Key = 'PROD'; Match = '(?i)mat-prod-'; Label = 'PROD';      Version = $ResolvedBuildVersionProd }
)

$uploadedCount = 0
foreach ($group in $envGroups) {
    $envXml = @($xmlFiles | Where-Object { $_.FullName -match $group.Match })
    if (-not $envXml -or $envXml.Count -eq 0) {
        Write-Host "No XML files found for $($group.Key); skipping TestRail run creation for this environment."
        continue
    }

    $tmpEnvDir = Join-Path $env:AGENT_TEMPDIRECTORY ("testrail-upload-" + $group.Key.ToLower())
    if (Test-Path $tmpEnvDir) {
        Remove-Item -Path $tmpEnvDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Path $tmpEnvDir -Force | Out-Null

    foreach ($f in $envXml) {
        Copy-Item -Path $f.FullName -Destination (Join-Path $tmpEnvDir $f.Name) -Force
    }

    $envVersionToken = [string]$group.Version
    if ([string]::IsNullOrWhiteSpace($envVersionToken)) {
        $envVersionToken = $versionToken
    }

    $envRunName = "hpx_rebrand_win_mat_${envVersionToken}_REBRAND_$($group.Label)"
    $args = @(
        "--artifact-dir", "`"$tmpEnvDir`"",
        "--run-name", "`"$envRunName`"",
        "--testrail-plan-name", "`"$matPlanName`"",
        "--testrail-milestone-id", "`"$fixedMilestoneId`""
    )
    if ($envVersionToken -ne "latest") {
        $args += "--version", "`"$envVersionToken`""
    }

    Write-Host "Running ($($group.Key)): python $scriptPath $($args -join ' ')"
    python $scriptPath @args
    if ($LASTEXITCODE -ne 0) {
        throw "TestRail upload failed for environment $($group.Key) with exit code $LASTEXITCODE"
    }
    $uploadedCount++
}

if ($uploadedCount -eq 0) {
    throw "No environment-specific XML groups matched (mat-itg-/mat-stg-/mat-prod-). Cannot create TestRail runs."
}

Write-Host "Created/updated $uploadedCount TestRail run(s) under milestone $fixedMilestoneId."
