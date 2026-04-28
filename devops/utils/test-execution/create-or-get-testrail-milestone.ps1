<#
.SYNOPSIS
    Creates or retrieves a TestRail milestone for test result tracking.

.DESCRIPTION
    This script manages TestRail milestones for daily and RC test runs.
    It generates milestone names based on the current date and milestone type,
    searches for existing milestones, or creates new ones if needed.
    
    Milestone Naming Convention:
    - Daily: "HP APP YYYY.MM.Daily" (e.g., "HP APP 2025.01.Daily")
    - RC: "HP APP YYYY.MM RC" (e.g., "HP APP 2025.01 RC")
    
    Date Range: Both milestone types use the current month's start and end dates.

.PARAMETER milestoneType
    Type of milestone to create or retrieve. Valid values: "Daily" or "RC"

.PARAMETER testrailUrl
    TestRail API base URL (e.g., "https://hp-testrail.external.hp.com/index.php?/api/v2/")

.PARAMETER testrailUser
    TestRail username for API authentication

.PARAMETER testrailApiKey
    TestRail API key for authentication

.PARAMETER projectId
    TestRail project ID where milestone will be created

.OUTPUTS
    Sets Azure DevOps pipeline variable: TESTRAIL_MILESTONE_ID

.EXAMPLE
    .\create-or-get-testrail-milestone.ps1 -milestoneType "Daily" -testrailUrl $env:TESTRAIL_URL -testrailUser $env:TESTRAIL_USER_NAME -testrailApiKey $env:TESTRAIL_API_KEY -projectId $env:TESTRAIL_PROJECT_ID
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Daily", "RC")]
    [string]$milestoneType,
    
    [Parameter(Mandatory=$true)]
    [string]$testrailUrl,
    
    [Parameter(Mandatory=$true)]
    [string]$testrailUser,
    
    [Parameter(Mandatory=$true)]
    [string]$testrailApiKey,
    
    [Parameter(Mandatory=$true)]
    [string]$projectId
)

# Generate milestone name based on type and current date
$currentDate = Get-Date
$year = $currentDate.Year
$month = $currentDate.ToString("MM")

if ($milestoneType -eq "Daily") {
    $milestoneName = "HP APP $year.$month.Daily"
} else {
    $milestoneName = "HP APP $year.$month RC"
}

Write-Host "Looking for milestone: $milestoneName"

# Calculate month start and end dates for milestone date range
$monthStart = Get-Date -Year $year -Month $currentDate.Month -Day 1
$monthEnd = $monthStart.AddMonths(1).AddDays(-1)

# Convert to Unix timestamp (seconds since epoch) for TestRail API
$startDateUnix = [int][double]::Parse(($monthStart.ToUniversalTime() - (Get-Date "1970-01-01")).TotalSeconds)
$endDateUnix = [int][double]::Parse(($monthEnd.ToUniversalTime() - (Get-Date "1970-01-01")).TotalSeconds)

Write-Host "Milestone date range: $($monthStart.ToString('yyyy-MM-dd')) to $($monthEnd.ToString('yyyy-MM-dd'))"

# Normalize TestRail URL - ensure it ends with /index.php?/api/v2/
$testrailUrl = $testrailUrl.TrimEnd('/')
if (-not $testrailUrl.EndsWith('/index.php?/api/v2')) {
    if ($testrailUrl.EndsWith('/index.php?/api/v2/')) {
        $testrailUrl = $testrailUrl.TrimEnd('/')
    } else {
        $testrailUrl = "$testrailUrl/index.php?/api/v2"
    }
}
$testrailUrl = "$testrailUrl/"

Write-Host "Using TestRail API URL: $testrailUrl"

# Setup API authentication
$base64AuthInfo = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${testrailUser}:${testrailApiKey}"))
$headers = @{
    "Authorization" = "Basic $base64AuthInfo"
    "Content-Type" = "application/json"
}

# Search for existing milestone by name
try {
    # Add is_completed=0 filter to get parent milestones (incomplete ones)
    # Note: TestRail API uses & for query parameters, not ?
    $getMilestonesUrl = "${testrailUrl}get_milestones/${projectId}&is_completed=0"
    Write-Host "Searching for existing milestones at: $getMilestonesUrl"
    
    # Use Invoke-WebRequest to get raw JSON, then parse manually
    # This prevents PowerShell from auto-flattening the nested milestones arrays
    $webResponse = Invoke-WebRequest -Uri $getMilestonesUrl -Method Get -Headers $headers -UseBasicParsing
    $jsonResponse = $webResponse.Content | ConvertFrom-Json
    
    # Find all milestones with matching name
    $matchingMilestones = $jsonResponse | Where-Object { $_.name -eq $milestoneName }
    
    if ($matchingMilestones) {
        # Check for duplicates
        if ($matchingMilestones.Count -gt 1) {
            Write-Host "##vso[task.logissue type=warning]Found $($matchingMilestones.Count) milestones with name '$milestoneName'. Using the most recent non-completed one."
            # Prefer non-completed milestones, then sort by ID descending (most recent)
            $existingMilestone = $matchingMilestones | Where-Object { -not $_.is_completed } | Sort-Object -Property id -Descending | Select-Object -First 1
            if (-not $existingMilestone) {
                # All are completed, use the most recent
                $existingMilestone = $matchingMilestones | Sort-Object -Property id -Descending | Select-Object -First 1
            }
        } else {
            $existingMilestone = $matchingMilestones
        }
        
        Write-Host "##[section]Found existing milestone: $milestoneName (ID: $($existingMilestone.id), Completed: $($existingMilestone.is_completed))"
        $milestoneId = $existingMilestone.id
    } else {
        Write-Host "##[section]Milestone not found. Creating new milestone: $milestoneName"
        
        # Create new milestone
        $addMilestoneUrl = "${testrailUrl}add_milestone/$projectId"
        $milestoneData = @{
            name = $milestoneName
            description = "Automated test results for $milestoneName"
            start_on = $startDateUnix
            due_on = $endDateUnix
        } | ConvertTo-Json
        
        $newMilestone = Invoke-RestMethod -Uri $addMilestoneUrl -Method Post -Headers $headers -Body $milestoneData
        $milestoneId = $newMilestone.id
        
        Write-Host "##[section]Created new milestone: $milestoneName (ID: $milestoneId)"
    }
    
    # Set Azure DevOps pipeline variable for downstream tasks
    Write-Host "##vso[task.setvariable variable=TESTRAIL_MILESTONE_ID;]$milestoneId"
    Write-Host "##[section]Set pipeline variable TESTRAIL_MILESTONE_ID = $milestoneId"
    
    exit 0
    
} catch {
    Write-Host "##vso[task.logissue type=error]Failed to create or retrieve TestRail milestone: $_"
    Write-Host "##vso[task.logissue type=error]Response: $($_.Exception.Response)"
    Write-Host "##vso[task.logissue type=error]StatusCode: $($_.Exception.Response.StatusCode.value__)"
    Write-Host "##vso[task.logissue type=error]StatusDescription: $($_.Exception.Response.StatusDescription)"
    exit 1
}
