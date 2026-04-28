# Generate Marker Matrix - Create Azure DevOps execution matrix from test marker requirements
#
# This script reads marker requirements JSON (from parse-test-markers.py), queries the Azure DevOps
# REST API to get agent capabilities from the ASQE-QAMA-General pool, matches requirements to
# available agents, deduplicates by platform×device combination, and outputs an ADO matrix JSON.
#
# Features:
# - Authenticates to Azure DevOps using PAT token from variable group
# - Queries agent capabilities from hardcoded ASQE-QAMA-General pool
# - Expands device-only markers to all platforms with that device capability
# - Deduplicates to first available agent per platform×device combo
# - ONLY includes combinations with available agents in matrix
# - Generates detailed report of valid vs invalid combinations
# - Generates job names like "Execute_CashmereXI_Roo"
#
# Usage:
#   generate-marker-matrix.ps1 -RequirementsFile <path> [-Organization <org>] [-Project <project>]
#
# Example:
#   generate-marker-matrix.ps1 -RequirementsFile marker-requirements.json

param(
    [Parameter(Mandatory=$true)]
    [string]$RequirementsFile,
    
    [Parameter(Mandatory=$false)]
    [string]$Organization = "hpcodeway",
    
    [Parameter(Mandatory=$false)]
    [string]$Project = "ASQE",
    
    [Parameter(Mandatory=$false)]
    [string]$PoolName = "ASQE-QAMA-General",
    
    [Parameter(Mandatory=$false)]
    [string]$AdditionalMarkerFilter = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$RequireRobotics
)

# Azure DevOps API version
$ApiVersion = "6.0"

# Helper function to format display names
function Format-DisplayName {
    param(
        [string]$Platform,
        [string]$Device
    )
    
    $parts = @()
    
    if ($Platform) {
        # Capitalize first letter, keep rest as-is
        $platformFormatted = $Platform.Substring(0,1).ToUpper() + $Platform.Substring(1)
        $parts += "Executing on $platformFormatted"
    }
    
    if ($Device) {
        # Split multiple devices by underscore and capitalize each
        $devices = $Device -split '_'
        $devicesFormatted = @()
        foreach ($d in $devices) {
            $devicesFormatted += $d.Substring(0,1).ToUpper() + $d.Substring(1)
        }
        
        if ($parts.Count -gt 0) {
            # Platform exists, add "with"
            $parts += "with"
        }
        else {
            # No platform, just say "Executing with"
            $parts += "Executing with"
        }
        
        if ($devicesFormatted.Count -eq 1) {
            $parts += $devicesFormatted[0]
        }
        elseif ($devicesFormatted.Count -eq 2) {
            $parts += "$($devicesFormatted[0]) and $($devicesFormatted[1])"
        }
        else {
            # More than 2 devices
            $lastDevice = $devicesFormatted[-1]
            $otherDevices = $devicesFormatted[0..($devicesFormatted.Count - 2)]
            $parts += ($otherDevices -join ', ') + ", and $lastDevice"
        }
    }
    
    return $parts -join ' '
}

# Read requirements file
Write-Host "Reading marker requirements from: $RequirementsFile"
if (-not (Test-Path $RequirementsFile)) {
    Write-Error "Requirements file not found: $RequirementsFile"
    exit 1
}

$requirementsData = Get-Content $RequirementsFile -Raw | ConvertFrom-Json
$requirements = $requirementsData.requirements
$testCases = $requirementsData.test_cases

Write-Host "Found $($requirements.Count) platform×device requirements"
Write-Host "Found $($testCases.Count) test cases"

if ($requirementsData.summary -and $requirementsData.summary.PSObject.Properties['skipped_test_cases']) {
    $skippedCount = [int]$requirementsData.summary.skipped_test_cases
    if ($skippedCount -gt 0) {
        Write-Host "##[warning]Excluded skip-marked tests from matrix generation: $skippedCount"
    }
    else {
        Write-Host "Excluded skip-marked tests from matrix generation: 0"
    }
}

# Filter test cases based on additional marker filter (e.g., "not robotics")
if ($AdditionalMarkerFilter -ne "") {
    Write-Host "`nApplying additional marker filter: $AdditionalMarkerFilter"
    
    $filteredTestCases = @()
    foreach ($testCase in $testCases) {
        $shouldInclude = $true
        
        # Check if filter contains "not robotics" or similar exclusions
        if ($AdditionalMarkerFilter -match 'not\s+(\w+)') {
            $excludeMarker = $matches[1]
            # Check if test case has the excluded marker in its file path or markers
            if ($testCase.file -match $excludeMarker) {
                $shouldInclude = $false
                Write-Host "  Excluding test: $($testCase.method) (has '$excludeMarker' marker)"
            }
        }
        
        if ($shouldInclude) {
            $filteredTestCases += $testCase
        }
    }
    
    $excludedCount = $testCases.Count - $filteredTestCases.Count
    Write-Host "Filtered test cases: $($filteredTestCases.Count) (excluded: $excludedCount)"
    $testCases = $filteredTestCases
    
    # Rebuild requirements from filtered test cases (generate cartesian product)
    Write-Host "`nRebuilding requirements from filtered test cases..."
    $requirements = @()
    $uniqueReqs = @{}
    
    foreach ($testCase in $testCases) {
        $platforms = $testCase.platforms
        $devices = $testCase.devices
        
        # Generate platform×device cartesian product (same logic as parse-test-markers.py)
        if ($platforms -and $platforms.Count -gt 0 -and $devices -and $devices.Count -gt 0) {
            # Both markers: create platform×device combinations
            foreach ($platform in $platforms) {
                foreach ($device in $devices) {
                    $key = "$platform|$device"
                    if (-not $uniqueReqs.ContainsKey($key)) {
                        $uniqueReqs[$key] = @{
                            platform = $platform
                            device = $device
                        }
                    }
                }
            }
        }
        elseif ($platforms -and $platforms.Count -gt 0) {
            # Platform only: create platform entries without device
            foreach ($platform in $platforms) {
                $key = "$platform|"
                if (-not $uniqueReqs.ContainsKey($key)) {
                    $uniqueReqs[$key] = @{
                        platform = $platform
                        device = $null
                    }
                }
            }
        }
        elseif ($devices -and $devices.Count -gt 0) {
            # Device only: create device entries without platform
            foreach ($device in $devices) {
                $key = "|$device"
                if (-not $uniqueReqs.ContainsKey($key)) {
                    $uniqueReqs[$key] = @{
                        platform = $null
                        device = $device
                    }
                }
            }
        }
    }
    
    $requirements = @($uniqueReqs.Values)
    Write-Host "Rebuilt requirements: $($requirements.Count) unique platform×device combinations"
}

# Get PAT token from environment variable (set by pipeline from variable group)
$pat = $env:AZUREDEVOPSPAT
if ([string]::IsNullOrEmpty($pat)) {
    Write-Error "ERROR: AzureDevOpsPAT environment variable not set"
    Write-Error "Ensure the 'secrets' variable group is linked and AzureDevOpsPAT is defined"
    exit 1
}

# Create authentication header
$encodedPat = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$pat"))
$headers = @{
    Authorization = "Basic $encodedPat"
    "Content-Type" = "application/json"
}

# Step 1: Get pool ID from pool name
Write-Host "`nQuerying Azure DevOps for pool: $PoolName"
$poolsUrl = "https://dev.azure.com/$Organization/_apis/distributedtask/pools?api-version=$ApiVersion"

try {
    $poolsResponse = Invoke-RestMethod -Uri $poolsUrl -Headers $headers -Method Get
    $pool = $poolsResponse.value | Where-Object { $_.name -eq $PoolName }
    
    if (-not $pool) {
        Write-Error "ERROR: Pool '$PoolName' not found in organization '$Organization'"
        Write-Error "Available pools: $($poolsResponse.value.name -join ', ')"
        exit 1
    }
    
    $poolId = $pool.id
    Write-Host "Found pool '$PoolName' (ID: $poolId)"
}
catch {
    Write-Error "ERROR: Failed to query Azure DevOps pools: $($_.Exception.Message)"
    exit 1
}

# Step 2: Get agents with capabilities from the pool
Write-Host "`nQuerying agents in pool '$PoolName'..."
$agentsUrl = "https://dev.azure.com/$Organization/_apis/distributedtask/pools/$poolId/agents?includeCapabilities=true&api-version=$ApiVersion"

try {
    $agentsResponse = Invoke-RestMethod -Uri $agentsUrl -Headers $headers -Method Get
    $agents = $agentsResponse.value
    
    Write-Host "Found $($agents.Count) agents in pool"
}
catch {
    Write-Error "ERROR: Failed to query agents: $($_.Exception.Message)"
    exit 1
}

# Step 3: Process agents and build capability map
Write-Host "`nProcessing agent capabilities..."
$agentCapabilities = @()

foreach ($agent in $agents) {
    try {
        $agentInfo = @{
            Name = $agent.name
            Id = $agent.id
            Status = $agent.status
            Enabled = $agent.enabled
            Platform = $null
            Robotics = $false
            Devices = @()
        }
        
        # Extract Platform capability (preserve original casing)
        if ($agent.systemCapabilities -and $agent.systemCapabilities.PSObject.Properties['Platform']) {
            $agentInfo.Platform = $agent.systemCapabilities.Platform
        }
        elseif ($agent.userCapabilities -and $agent.userCapabilities.PSObject.Properties['Platform']) {
            $agentInfo.Platform = $agent.userCapabilities.Platform
        }
        
        # Store lowercase version for case-insensitive matching
        $agentInfo.PlatformLower = if ($agentInfo.Platform) { $agentInfo.Platform.ToLower() } else { $null }
        
        # Extract device capabilities (boolean capabilities set to true)
        $allCapabilities = @{}
        if ($agent.systemCapabilities -and $agent.systemCapabilities.PSObject.Properties) {
            foreach ($prop in $agent.systemCapabilities.PSObject.Properties) {
                $allCapabilities[$prop.Name] = $prop.Value
            }
        }
        if ($agent.userCapabilities -and $agent.userCapabilities.PSObject.Properties) {
            foreach ($prop in $agent.userCapabilities.PSObject.Properties) {
                $allCapabilities[$prop.Name] = $prop.Value
            }
        }
        
        if ($allCapabilities.Keys) {
            foreach ($capName in @($allCapabilities.Keys)) {
                $capValue = $allCapabilities[$capName]
                # Boolean capabilities: Robotics is tracked separately; all others are device flags
                if ($capValue -eq 'true' -or $capValue -eq $true) {
                    if ($capName -eq 'Robotics') {
                        $agentInfo.Robotics = $true
                    }
                    elseif ($capName -ne 'Platform') {
                        $agentInfo.Devices += $capName.ToLower()
                    }
                }
            }
        }
        
        $agentCapabilities += $agentInfo
        
        $deviceList = if ($agentInfo.Devices.Count -gt 0) { $agentInfo.Devices -join ', ' } else { '<none>' }
        Write-Host "  Agent: $($agentInfo.Name) | Platform: $($agentInfo.Platform) | Robotics: $($agentInfo.Robotics) | Devices: $deviceList | Status: $($agentInfo.Status) | Enabled: $($agentInfo.Enabled)"
    }
    catch {
        Write-Error "Failed to process agent $($agent.name): $_"
        Write-Error "Error details: $($_.Exception.Message)"
        Write-Error "Stack trace: $($_.ScriptStackTrace)"
        throw
    }
}

# Step 4: Expand device-only requirements to all platforms with that device
Write-Host "`nExpanding device-only requirements..."
$expandedRequirements = @()

foreach ($req in $requirements) {
    if ($req.platform -and $req.device) {
        # Both platform and device specified - use as-is
        $expandedRequirements += $req
    }
    elseif ($req.platform -and -not $req.device) {
        # Platform only - use as-is
        $expandedRequirements += $req
    }
    elseif (-not $req.platform -and $req.device) {
        # Device only - expand to all unique platforms with this device
        $deviceName = $req.device.ToLower()
        $platformsWithDevice = @($agentCapabilities | 
            Where-Object { $_.Devices -contains $deviceName -and $_.Platform -and $_.Enabled -eq $true -and $_.Status -eq 'online' } |
            Select-Object -ExpandProperty Platform -Unique)
        
        if ($platformsWithDevice.Count -eq 0 -or $null -eq $platformsWithDevice[0]) {
            Write-Warning "  No platforms found with device '$($req.device)' - will include in matrix for timeout"
            # Still add to expanded requirements with null platform
            $expandedRequirements += $req
        }
        else {
            Write-Host "  Expanded device '$($req.device)' to $($platformsWithDevice.Count) platforms"
            foreach ($platform in $platformsWithDevice) {
                $expandedRequirements += @{
                    platform = $platform
                    device = $req.device
                }
            }
        }
    }
}

Write-Host "Expanded to $($expandedRequirements.Count) total requirements"

# Step 4b: Filter agents to Robotics-capable only (if required)
if ($RequireRobotics) {
    $beforeCount = $agentCapabilities.Count
    $agentCapabilities = @($agentCapabilities | Where-Object { $_.Robotics -eq $true })
    $filteredCount = $beforeCount - $agentCapabilities.Count
    Write-Host "`nRobotics filter applied: $($agentCapabilities.Count) of $beforeCount agents have Robotics=True (excluded: $filteredCount)"
    if ($agentCapabilities.Count -eq 0) {
        Write-Host "##[warning]No agents with Robotics=True capability found in pool '$PoolName'"
    }
}

# Step 5: Match requirements to agents and build matrix

$matrix = @{}
$validEntries = @()
$invalidEntries = @()

foreach ($req in $expandedRequirements) {
    $platform = $req.platform
    $device = $req.device
    
    # Create unique key for deduplication
    $platformKey = if ($platform) { $platform.ToLower() } else { "ANY" }
    $deviceKey = if ($device) { $device.ToLower() } else { "NONE" }
    $uniqueKey = "$platformKey|$deviceKey"
    
    # Skip if already processed this combination
    if ($matrix.ContainsKey($uniqueKey)) {
        continue
    }
    
    # Find matching agent
    $matchingAgent = $null
    
    if ($platform -and $device) {
        # Match both platform and device (case-insensitive platform matching)
        $platformLower = $platform.ToLower()
        $deviceLower = $device.ToLower()
        
        # Debug: Show all agents and why they match or don't match
        Write-Host "  Searching for: Platform='$platform' (lower: '$platformLower'), Device='$device' (lower: '$deviceLower')"
        foreach ($agent in $agentCapabilities) {
            $platformMatch = $agent.PlatformLower -eq $platformLower
            $deviceMatch = $agent.Devices -contains $deviceLower
            $enabledMatch = $agent.Enabled -eq $true
            $onlineMatch = $agent.Status -eq 'online'
            $match = $platformMatch -and $deviceMatch -and $enabledMatch -and $onlineMatch
            
            if ($match -or $platformMatch) {
                Write-Host "    Agent: $($agent.Name) | Platform: $($agent.PlatformLower) | Devices: $($agent.Devices -join ',') | Enabled: $($agent.Enabled)"
                Write-Host "      Platform Match: $platformMatch | Device Match: $deviceMatch | Enabled: $enabledMatch | Online: $onlineMatch | Overall: $match"
            }
        }
        
        $matchingAgent = $agentCapabilities | Where-Object {
            $_.PlatformLower -eq $platformLower -and $_.Devices -contains $deviceLower -and $_.Enabled -eq $true -and $_.Status -eq 'online'
        } | Select-Object -First 1
        
        if ($matchingAgent) {
            Write-Host "    => MATCHED: $($matchingAgent.Name)"
        } else {
            Write-Host "    => NO MATCH FOUND"
        }
    }
    elseif ($platform -and -not $device) {
        # Match platform only (case-insensitive)
        $platformLower = $platform.ToLower()
        $matchingAgent = $agentCapabilities | Where-Object {
            $_.PlatformLower -eq $platformLower -and $_.Enabled -eq $true -and $_.Status -eq 'online'
        } | Select-Object -First 1
    }
    elseif (-not $platform -and $device) {
        # Device only without platform expansion (shouldn't happen after expansion, but handle it)
        $deviceLower = $device.ToLower()
        $matchingAgent = $agentCapabilities | Where-Object {
            $_.Devices -contains $deviceLower -and $_.Enabled -eq $true -and $_.Status -eq 'online'
        } | Select-Object -First 1
    }
    
    # Create matrix entry with formatted job name
    $jobName = Format-DisplayName -Platform $platform -Device $device
    # Create formatted matrix key - capitalize properly, use spaces
    # Azure DevOps will append this to the job displayName
    $matrixKey = ""
    if ($platform) {
        # Capitalize first letter of platform
        $platformFormatted = $platform.Substring(0,1).ToUpper() + $platform.Substring(1)
        $matrixKey += $platformFormatted
    }
    if ($device) {
        if ($matrixKey) { $matrixKey += " with " }
        # Handle multiple devices separated by underscore
        $devices = $device -split '_'
        $devicesFormatted = @()
        foreach ($d in $devices) {
            $devicesFormatted += $d.Substring(0,1).ToUpper() + $d.Substring(1)
        }
        if ($devicesFormatted.Count -eq 1) {
            $matrixKey += $devicesFormatted[0]
        }
        elseif ($devicesFormatted.Count -eq 2) {
            $matrixKey += "$($devicesFormatted[0]) and $($devicesFormatted[1])"
        }
        else {
            $lastDevice = $devicesFormatted[-1]
            $otherDevices = $devicesFormatted[0..($devicesFormatted.Count - 2)]
            $matrixKey += ($otherDevices -join ', ') + ", and $lastDevice"
        }
    }
    
    $entry = @{
        jobName = $jobName
        matrixKey = $matrixKey
        platform = $platform
        device = $device
        agentName = if ($matchingAgent) { $matchingAgent.Name } else { $null }
        agentPlatform = if ($matchingAgent) { $matchingAgent.Platform } else { $null }
        available = if ($matchingAgent) { $true } else { $false }
    }
    
    # Separate valid and invalid entries
    if ($matchingAgent) {
        $matrix[$uniqueKey] = $entry
        $validEntries += $entry
    }
    else {
        $invalidEntries += $entry
    }
}

# Step 6: Generate Azure DevOps matrix JSON format (only valid entries)
Write-Host "`nGenerating Azure DevOps matrix..."
$adoMatrix = @{}

foreach ($entry in $validEntries) {
    $matrixKey = $entry.matrixKey
    
    $matrixValue = @{
        platformName = if ($entry.platform) { $entry.platform } else { "" }
        deviceName = if ($entry.device) { $entry.device } else { "" }
        agentAvailable = $entry.available
    }
    
    # Add agent name for logging/display
    if ($entry.agentName) {
        $matrixValue.agentName = $entry.agentName
    }
    
    # Add agent Platform capability for demand
    if ($entry.agentPlatform) {
        $matrixValue.agentPlatform = $entry.agentPlatform
    }
    
    # Add formatted display name
    $matrixValue.displayName = $entry.jobName
    
    $adoMatrix[$matrixKey] = $matrixValue
}

# Step 7: Skip detailed agent matching report (redundant with test execution report below)

# Helper function to categorize why a test won't execute
function Get-SkipReason {
    param($test, $agentCapabilities, $validEntries)
    
    $platforms = $test.platforms
    $devices = $test.devices
    
    # Check if test is missing platform marker (device marker is optional)
    if ((-not $platforms -or $platforms.Count -eq 0)) {
        return @{
            Category = "missing_platform_marker"
            Reason = "Test missing @pytest.mark.platform() marker"
        }
    }
    
    # Check if it's a platform issue or device issue
    if ($platforms -and $platforms.Count -gt 0) {
        # Check if any platform exists
        $platformExists = $false
        foreach ($platform in $platforms) {
            $platformLower = $platform.ToLower()
            $agentWithPlatform = $agentCapabilities | Where-Object { 
                $_.PlatformLower -eq $platformLower -and $_.Enabled -eq $true -and $_.Status -eq 'online' 
            }
            if ($agentWithPlatform) {
                $platformExists = $true
                break
            }
        }
        
        if (-not $platformExists) {
            return @{
                Category = "missing_platform"
                Reason = "No agents exist for platform(s): $($platforms -join ', ')"
            }
        }
    }
    
    # If we have devices and platforms exist, it's a device issue
    if ($devices -and $devices.Count -gt 0) {
        return @{
            Category = "missing_device"
            Reason = "Platform exists but missing '$($devices -join ', ')' device capability"
            Device = $devices[0]
        }
    }
    
    # Generic case
    return @{
        Category = "other"
        Reason = "No compatible agent available"
    }
}

# Helper function to extract suite name from test case
function Get-SuiteName {
    param($test)
    
    if ($test.class) {
        return $test.class
    }
    
    # Extract from file name if no class
    $fileName = Split-Path $test.file -Leaf
    return $fileName -replace '\.py$', ''
}

# Step 8: Generate test case reports
Write-Host "`n$('=' * 80)"
Write-Host "TEST CASE EXECUTION REPORT"
Write-Host $('=' * 80)

# Categorize test cases
$testCasesWillRun = @()
$testCasesWillNotRun = @()

foreach ($testCase in $testCases) {
    $platforms = $testCase.platforms
    $devices = $testCase.devices
    
    # Determine if this test case will run
    $willRun = $false
    
    if ($platforms -and $devices) {
        # Test requires both platform and device - check if any combo is valid
        foreach ($platform in $platforms) {
            foreach ($device in $devices) {
                $combo = $validEntries | Where-Object { 
                    $_.platform -eq $platform -and $_.device -eq $device 
                }
                if ($combo) {
                    $willRun = $true
                    break
                }
            }
            if ($willRun) { break }
        }
    }
    elseif ($platforms) {
        # Test requires only platform
        foreach ($platform in $platforms) {
            $combo = $validEntries | Where-Object { $_.platform -eq $platform }
            if ($combo) {
                $willRun = $true
                break
            }
        }
    }
    elseif ($devices) {
        # Test requires only device
        foreach ($device in $devices) {
            $combo = $validEntries | Where-Object { $_.device -eq $device }
            if ($combo) {
                $willRun = $true
                break
            }
        }
    }
    
    if ($willRun) {
        $testCasesWillRun += $testCase
    }
    else {
        $testCasesWillNotRun += $testCase
    }
}

if ($testCasesWillRun.Count -gt 0) {
    Write-Host "`n[TESTS THAT WILL EXECUTE] - $($testCasesWillRun.Count) test cases:"
    Write-Host $('-' * 80)
    foreach ($test in $testCasesWillRun) {
        $testName = if ($test.class) { "$($test.class)::$($test.method)" } else { $test.method }
        $platformList = if ($test.platforms) { $test.platforms -join ', ' } else { '<none>' }
        $deviceList = if ($test.devices) { $test.devices -join ', ' } else { '<none>' }
        Write-Host "  $testName"
        Write-Host "    File: $($test.file):$($test.line)"
        Write-Host "    Platforms: $platformList | Devices: $deviceList"
    }
}

if ($testCasesWillNotRun.Count -gt 0) {
    Write-Host "`n$('=' * 80)"
    Write-Host "TESTS THAT WON'T EXECUTE - ORGANIZED BY TEST SUITE & SKIP REASON"
    Write-Host $('=' * 80)
    
    # Group tests by suite
    $testsBySuite = @{}
    foreach ($test in $testCasesWillNotRun) {
        $suiteName = Get-SuiteName -test $test
        if (-not $testsBySuite.ContainsKey($suiteName)) {
            $testsBySuite[$suiteName] = @()
        }
        $testsBySuite[$suiteName] += $test
    }
    
    # Process each suite
    foreach ($suiteName in ($testsBySuite.Keys | Sort-Object)) {
        $suiteTests = $testsBySuite[$suiteName]
        $fileName = Split-Path $suiteTests[0].file -Leaf
        
        Write-Host ""
        Write-Host $('+' + ('-' * 98) + '+')
        Write-Host "| Test Suite: $suiteName$(' ' * (84 - $suiteName.Length)) |"
        Write-Host "| File: $fileName$(' ' * (90 - $fileName.Length)) |"
        Write-Host "| Tests in Suite: $($suiteTests.Count) tests$(' ' * (71 - $($suiteTests.Count).ToString().Length)) |"
        Write-Host $('+' + ('-' * 98) + '+')
        Write-Host ""
        
        # Categorize tests within suite
        $categorized = @{
            missing_platform_marker = @()
            missing_device = @()
            missing_platform = @()
            other = @()
        }
        
        foreach ($test in $suiteTests) {
            $skipInfo = Get-SkipReason -test $test -agentCapabilities $agentCapabilities -validEntries $validEntries
            $categorized[$skipInfo.Category] += @{
                Test = $test
                SkipInfo = $skipInfo
            }
        }
        
        # Print by category
        foreach ($category in @('missing_platform_marker', 'missing_device', 'missing_platform', 'other')) {
            $testsInCategory = $categorized[$category]
            if ($testsInCategory.Count -eq 0) { continue }
            
            if ($category -eq 'missing_platform_marker') {
                Write-Host "  SKIP REASON: Missing Platform Marker ($($testsInCategory.Count) tests)"
                Write-Host "  $('-' * 96)"
                foreach ($item in $testsInCategory) {
                    Write-Host "    [X] $($item.Test.method)"
                }
                Write-Host ""
                Write-Host "    Problem:  Tests are missing @pytest.mark.platform() marker"
                Write-Host "    Action:   Add platform marker to test methods"
                Write-Host "    Example:  @pytest.mark.platform('MasadaN')"
                Write-Host ""
            }
            elseif ($category -eq 'missing_device') {
                # Group by device type
                $deviceGroups = @{}
                foreach ($item in $testsInCategory) {
                    $device = if ($item.SkipInfo.Device) { $item.SkipInfo.Device } else { "unknown" }
                    if (-not $deviceGroups.ContainsKey($device)) {
                        $deviceGroups[$device] = @()
                    }
                    $deviceGroups[$device] += $item
                }
                
                foreach ($device in ($deviceGroups.Keys | Sort-Object)) {
                    $deviceTests = $deviceGroups[$device]
                    
                    if ($deviceTests.Count -eq $suiteTests.Count) {
                        Write-Host "  SKIP REASON: Missing Device Capability - All $($suiteTests.Count) tests require '$device' device"
                    }
                    else {
                        Write-Host "  SKIP REASON: Missing Device Capability ($($deviceTests.Count) tests)"
                    }
                    Write-Host "  $('-' * 96)"
                    
                    foreach ($item in $deviceTests) {
                        Write-Host "    [X] $($item.Test.method)"
                    }
                    
                    # Show details for first test
                    $firstTest = $deviceTests[0].Test
                    Write-Host ""
                    Write-Host "    Required: $($firstTest.platforms -join ', ') platform WITH '$device' device"
                    Write-Host "    Problem:  Agents exist but lack '$device' device capability"
                    Write-Host ""
                }
            }
            elseif ($category -eq 'missing_platform') {
                Write-Host "  SKIP REASON: Missing Platform or Platform/Device Combo ($($testsInCategory.Count) tests)"
                Write-Host "  $('-' * 96)"
                foreach ($item in $testsInCategory) {
                    Write-Host "    [X] $($item.Test.method)"
                    $platformList = if ($item.Test.platforms) { $item.Test.platforms -join ', ' } else { '<none>' }
                    $deviceList = if ($item.Test.devices) { $item.Test.devices -join ', ' } else { '<none>' }
                    Write-Host "       Required: $platformList platform WITH '$deviceList' device"
                    Write-Host "       Problem:  $($item.SkipInfo.Reason)"
                }
                Write-Host ""
            }
            else {
                Write-Host "  SKIP REASON: Other ($($testsInCategory.Count) tests)"
                Write-Host "  $('-' * 96)"
                foreach ($item in $testsInCategory) {
                    Write-Host "    [X] $($item.Test.method)"
                }
                Write-Host ""
            }
        }
    }
}

Write-Host "`n$('=' * 80)"
Write-Host "SKIP REASON SUMMARY"
Write-Host $('=' * 80)

# Count by category
$missingPlatformMarkerCount = 0
$missingDeviceCount = 0
$missingPlatformCount = 0
$otherCount = 0

foreach ($test in $testCasesWillNotRun) {
    $skipInfo = Get-SkipReason -test $test -agentCapabilities $agentCapabilities -validEntries $validEntries
    if ($skipInfo.Category -eq 'missing_platform_marker') {
        $missingPlatformMarkerCount++
    }
    elseif ($skipInfo.Category -eq 'missing_device') {
        $missingDeviceCount++
    }
    elseif ($skipInfo.Category -eq 'missing_platform') {
        $missingPlatformCount++
    }
    else {
        $otherCount++
    }
}

if ($missingPlatformMarkerCount -gt 0) {
    Write-Host ""
    Write-Host "  $missingPlatformMarkerCount tests [X] Missing Platform Marker"
    Write-Host "     -> Tests lack @pytest.mark.platform() marker"
    Write-Host "     -> SOLUTION: Add platform marker to test methods:"
    Write-Host "        @pytest.mark.platform('MasadaN')"
}

if ($missingDeviceCount -gt 0) {
    Write-Host ""
    Write-Host "  $missingDeviceCount tests [X] Missing Device Capability"
    Write-Host "     -> Platforms exist but agents lack required device (trio, roo, moonracer)"
    Write-Host "     -> SOLUTION: Add device capabilities to existing agents"
}

if ($missingPlatformCount -gt 0) {
    Write-Host ""
    Write-Host "  $missingPlatformCount tests [X] Missing Platform or Platform/Device Combo"
    Write-Host "     -> No agents exist for required platform"
    Write-Host "     -> SOLUTION: Add agents for missing platforms or fix platform names"
}

if ($testCasesWillRun.Count -gt 0) {
    Write-Host ""
    Write-Host "  $($testCasesWillRun.Count) tests [PASS] Will Execute"
    Write-Host "     -> Platform and device requirements fully satisfied"
}

Write-Host ""

# Recommended Actions
if ($missingPlatformMarkerCount -gt 0 -or $missingDeviceCount -gt 0 -or $missingPlatformCount -gt 0) {
    Write-Host $('=' * 80)
    Write-Host "RECOMMENDED ACTIONS TO INCREASE TEST COVERAGE"
    Write-Host $('=' * 80)
    
    if ($missingPlatformMarkerCount -gt 0) {
        Write-Host ""
        Write-Host "  1. ADD PLATFORM MARKERS (Would enable $missingPlatformMarkerCount tests):"
        Write-Host "     $('-' * 73)"
        Write-Host "     - Add @pytest.mark.platform() marker to test methods"
        Write-Host "     - Example:"
        Write-Host "       @pytest.mark.platform('MasadaN')"
        Write-Host "       def test_my_feature():"
        Write-Host "           ..."
    }
    
    if ($missingDeviceCount -gt 0) {
        Write-Host ""
        Write-Host "  2. ADD DEVICE CAPABILITIES (Would enable $missingDeviceCount tests):"
        Write-Host "     $('-' * 73)"
        
        # Analyze which devices are needed
        $deviceNeeds = @{}
        foreach ($test in $testCasesWillNotRun) {
            $skipInfo = Get-SkipReason -test $test -agentCapabilities $agentCapabilities -validEntries $validEntries
            if ($skipInfo.Category -eq 'missing_device' -and $test.devices) {
                $device = $test.devices[0]
                if (-not $deviceNeeds.ContainsKey($device)) {
                    $deviceNeeds[$device] = @()
                }
                
                # Find agents with the platform
                foreach ($platform in $test.platforms) {
                    $platformLower = $platform.ToLower()
                    $agents = $agentCapabilities | Where-Object {
                        $_.PlatformLower -eq $platformLower -and $_.Enabled -eq $true -and $_.Status -eq 'online'
                    }
                    foreach ($agent in $agents) {
                        if ($deviceNeeds[$device] -notcontains $agent.Name) {
                            $deviceNeeds[$device] += $agent.Name
                        }
                    }
                }
            }
        }
        
        foreach ($device in ($deviceNeeds.Keys | Sort-Object)) {
            $agents = $deviceNeeds[$device] | Sort-Object | Select-Object -First 8
            $agentList = $agents -join ', '
            if ($deviceNeeds[$device].Count -gt 8) {
                $agentList += ", ... and $($deviceNeeds[$device].Count - 8) more"
            }
            Write-Host "     Add '$device' to:    $agentList"
        }
    }
    
    if ($missingPlatformCount -gt 0) {
        Write-Host ""
        Write-Host "  3. FIX PLATFORM NAMING OR ADD MISSING PLATFORMS (Would enable $missingPlatformCount tests):"
        Write-Host "     $('-' * 73)"
        
        # Find missing platforms
        $missingPlatforms = @{}
        foreach ($test in $testCasesWillNotRun) {
            $skipInfo = Get-SkipReason -test $test -agentCapabilities $agentCapabilities -validEntries $validEntries
            if ($skipInfo.Category -eq 'missing_platform' -and $test.platforms) {
                foreach ($platform in $test.platforms) {
                    $platformLower = $platform.ToLower()
                    $exists = $agentCapabilities | Where-Object { $_.PlatformLower -eq $platformLower }
                    if (-not $exists) {
                        $missingPlatforms[$platform] = $true
                    }
                }
            }
        }
        
        foreach ($platform in ($missingPlatforms.Keys | Sort-Object)) {
            Write-Host "     Add agent for '$platform' platform OR update test to use existing platform"
        }
    }
    
    Write-Host ""
}

Write-Host $('=' * 80)
Write-Host "TEST EXECUTION SUMMARY"
Write-Host $('=' * 80)
Write-Host "Total test cases: $($testCases.Count)"
Write-Host "Will execute: $($testCasesWillRun.Count)"
Write-Host "Will NOT execute: $($testCasesWillNotRun.Count)"
Write-Host $('=' * 80)

# Warn if tests won't execute due to missing agents
if ($invalidEntries.Count -gt 0) {
    Write-Host "##[warning]$($invalidEntries.Count) platform×device combination(s) skipped - no matching agents available"
    Write-Host "##[warning]$($testCasesWillNotRun.Count) test(s) will not execute"
}

# Step 9: Validate and set pipeline output variables
Write-Host "`nValidating matrix generation..."

# Check if matrix is empty
if ($validEntries.Count -eq 0) {
    Write-Host ""
    Write-Host "##[error]$('=' * 80)"
    Write-Host "##[error]CRITICAL ERROR: NO AGENTS AVAILABLE FOR TEST EXECUTION"
    Write-Host "##[error]$('=' * 80)"
    Write-Host "##[error]"
    Write-Host "##[error]All platform×device combinations were skipped due to missing agents"
    Write-Host "##[error]"
    Write-Host "##[error]REQUIRED ACTION:"
    Write-Host "##[error]  1. Check that agents in ASQE-QAMA-General pool are online and enabled"
    Write-Host "##[error]  2. Verify agents have required Platform and Device capabilities"
    Write-Host "##[error]  3. Review SKIPPED COMBINATIONS report above for details"
    Write-Host "##[error]"
    Write-Host "##[error]RESULT: Zero tests will execute - Stage will be skipped"
    Write-Host "##[error]$('=' * 80)"
    Write-Host ""
    
    # Set output variables to indicate no agents found
    Write-Host "##vso[task.setvariable variable=agentMatrix;isOutput=true]{}"
    Write-Host "##vso[task.setvariable variable=foundAgents;isOutput=true]false"
    Write-Host "##vso[task.setvariable variable=agentCount;isOutput=true]0"
    
    Write-Host "`n$('=' * 80)"
    Write-Host "Matrix generation complete - NO AGENTS AVAILABLE"
    Write-Host $('=' * 80)
    
    exit 1
}

Write-Host "Setting Azure DevOps pipeline variables..."

# Convert matrix to JSON
$matrixJson = $adoMatrix | ConvertTo-Json -Compress -Depth 10

# Determine if tests were found based on test case count
$foundTestsValue = if ($testCases.Count -gt 0) { "true" } else { "false" }

# Set output variables for pipeline
Write-Host "##vso[task.setvariable variable=agentMatrix;isOutput=true]$matrixJson"
Write-Host "##vso[task.setvariable variable=foundAgents;isOutput=true]true"
Write-Host "##vso[task.setvariable variable=foundTests;isOutput=true]$foundTestsValue"
Write-Host "##vso[task.setvariable variable=agentCount;isOutput=true]$($validEntries.Count)"

Write-Host "`nGenerated Matrix JSON:"
$adoMatrix | ConvertTo-Json -Depth 10 | Write-Host

Write-Host "`n$('=' * 80)"
Write-Host "Matrix generation complete - ready for execution"
Write-Host $('=' * 80)

# Exit with code 1 if there were any warnings (to trigger orange status with continueOnError)
if ($invalidEntries.Count -gt 0) {
    Write-Host "`nExiting with warning status due to skipped combinations"
    exit 1
}

exit 0
