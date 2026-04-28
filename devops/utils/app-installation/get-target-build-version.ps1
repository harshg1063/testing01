param(
    [Parameter(Mandatory=$true)]
    [string]$organization,
    
    [Parameter(Mandatory=$true)]
    [string]$project,
    
    [Parameter(Mandatory=$true)]
    [string]$pipelineId,
    
    [Parameter(Mandatory=$false)]
    [string]$providedBuildId = "",
    
    [Parameter(Mandatory=$false)]
    [string]$providedBuildVersion = "",
    
    [Parameter(Mandatory=$false)]
    [string]$buildVersionToDownload = "latest",
    
    [Parameter(Mandatory=$false)]
    [string]$branchName = "refs/heads/main",
    
    [Parameter(Mandatory=$true)]
    [string]$accessToken
)

$ErrorActionPreference = "Stop"

Write-Host "Pipeline ID: $pipelineId"
Write-Host "Build Version Strategy: $buildVersionToDownload"

$headers = @{
    Authorization = "Bearer $accessToken"
}

# Determine which build to use
if ($providedBuildId -ne "" -and $buildVersionToDownload -eq "specific") {
    # Use provided numeric build ID directly
    $buildId = $providedBuildId
    Write-Host "Using provided Build ID: $buildId"
    
    $buildUrl = "${organization}${project}/_apis/build/builds/${buildId}?api-version=7.0"
    $buildInfo = Invoke-RestMethod -Uri $buildUrl -Headers $headers -Method Get
} elseif ($providedBuildVersion -ne "" -and $buildVersionToDownload -eq "specific") {
    # Search for build by build number (version string like "53.42601.121.0")
    Write-Host "Searching for build with build number: $providedBuildVersion"
    
    $buildsUrl = "${organization}${project}/_apis/build/builds?definitions=${pipelineId}&api-version=7.0"
    Write-Host "Querying all builds from pipeline $pipelineId..."
    
    $buildsResponse = Invoke-RestMethod -Uri $buildsUrl -Headers $headers -Method Get
    
    # Find build matching the provided build number
    $buildInfo = $buildsResponse.value | Where-Object { $_.buildNumber -eq $providedBuildVersion } | Select-Object -First 1
    
    if (-not $buildInfo) {
        throw "Build with build number '$providedBuildVersion' not found in pipeline $pipelineId"
    }
    
    $buildId = $buildInfo.id
    Write-Host "Found build ID: $buildId for build number: $($buildInfo.buildNumber)"
} else {
    # Get latest successful build from pipeline
    if ($buildVersionToDownload -eq "latestFromBranch") {
        Write-Host "Getting latest successful build from pipeline $pipelineId from branch $branchName..."
        $buildsUrl = "${organization}${project}/_apis/build/builds?definitions=${pipelineId}&branchName=${branchName}&statusFilter=completed&resultFilter=succeeded&`$top=1&api-version=7.0"
    } else {
        Write-Host "Getting latest successful build from pipeline $pipelineId..."
        $buildsUrl = "${organization}${project}/_apis/build/builds?definitions=${pipelineId}&statusFilter=completed&resultFilter=succeeded&`$top=1&api-version=7.0"
    }
    
    Write-Host "Fetching latest builds from: $buildsUrl"
    
    $buildsResponse = Invoke-RestMethod -Uri $buildsUrl -Headers $headers -Method Get
    
    if ($buildsResponse.count -eq 0) {
        if ($buildVersionToDownload -eq "latestFromBranch") {
            throw "No successful builds found for pipeline $pipelineId from branch $branchName"
        } else {
            throw "No successful builds found for pipeline $pipelineId"
        }
    }
    
    $buildInfo = $buildsResponse.value[0]
    $buildId = $buildInfo.id
    Write-Host "Latest successful build ID: $buildId"
    Write-Host "Source Branch: $($buildInfo.sourceBranch)"
}

$targetVersion = $buildInfo.buildNumber
Write-Host "Build Number (Target Version): $targetVersion"
Write-Host "Build Status: $($buildInfo.status)"
Write-Host "Build Result: $($buildInfo.result)"

# Set output variables for Azure DevOps
Write-Host "##vso[task.setvariable variable=TargetVersion;isOutput=true]$targetVersion"
Write-Host "##vso[task.setvariable variable=ActualBuildId;isOutput=true]$buildId"
