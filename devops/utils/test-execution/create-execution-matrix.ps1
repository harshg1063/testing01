# Create Execution Matrix from Test Target Lookup Results
#
# Reads JSON from lookup-test-targets-by-platform-and-device.py and creates Azure DevOps execution matrix
# based on the cartesian product of platforms × devices
#
# Parameters:
#   -JsonFilePath: Path to lookup results JSON file
#   -PoolName: Agent pool name (for error messages)
#
# Output Variables:
#   - executionMatrix: JSON matrix for parallel execution (platform×device combinations)
#   - foundAgents: Boolean indicating if agents were found
#   - agentCount: Number of platform×device combinations

param(
    [Parameter(Mandatory=$true)]
    [string]$JsonFilePath,

    [Parameter(Mandatory=$false)]
    [string]$PoolName = "ASQE-QAMA-General"
)

$ErrorActionPreference = "Stop"

Write-Host "##[section]Creating Execution Matrix (Platform × Device Cartesian Product)"

# Read and validate lookup results
if (-not (Test-Path $JsonFilePath)) {
    Write-Host "##[error]Lookup results file not found: $JsonFilePath"
    exit 1
}

$lookupResults = Get-Content $JsonFilePath -Raw | ConvertFrom-Json

Write-Host "Platform Filter: $($lookupResults.platform)"
Write-Host "Device Filter: $($lookupResults.device)"
Write-Host "Total Agents: $($lookupResults.count)"

if ($lookupResults.count -eq 0) {
    Write-Host "##[error]No agents found matching criteria"
    Write-Host "##[error]Platform Filter: '$($lookupResults.platform)'"
    Write-Host "##[error]Device Filter: '$($lookupResults.device)'"
    Write-Host "##[error]Verify:"
    Write-Host "##[error]  1. Platform/Device names are spelled correctly"
    Write-Host "##[error]  2. Agents exist with matching capabilities"
    Write-Host "##[error]  3. Agents are in pool '$PoolName'"
    exit 1
}

# Step 1: Build list of online/enabled agents
$onlineAgents = @()
$offlineCount = 0

foreach ($agent in $lookupResults.test_targets) {
    if ($agent.status -eq 'online' -and $agent.enabled -eq $true) {
        # Store agent info for matching
        $agentInfo = @{
            Name = $agent.name
            Platform = $agent.platform
            PlatformLower = $agent.platform.ToLower()
            Devices = @($agent.devices | ForEach-Object { $_.ToLower() })
        }
        $onlineAgents += $agentInfo

        $deviceDisplay = if ($agent.devices.Count -gt 0) { $agent.devices -join ', ' } else { '<none>' }
        Write-Host "  [ONLINE] $($agent.name) → Platform: $($agent.platform) | Devices: $deviceDisplay"
    }
    else {
        $offlineCount++
        Write-Host "  [SKIP] $($agent.name) → Status: $($agent.status), Enabled: $($agent.enabled)"
    }
}

Write-Host ""
Write-Host "Online/Enabled Agents: $($onlineAgents.Count)"
Write-Host "Offline/Disabled Agents: $offlineCount"

if ($onlineAgents.Count -eq 0) {
    Write-Host "##[error]No online/enabled agents found matching criteria"
    Write-Host "##[error]All agents are either offline or disabled"
    exit 1
}

# Step 2: Extract unique platforms and devices from filters
$platformFilter = $lookupResults.platform
$deviceFilter = $lookupResults.device

# Parse comma-separated filters
$platforms = @()
if (-not [string]::IsNullOrWhiteSpace($platformFilter)) {
    $platforms = @($platformFilter -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

$devices = @()
if (-not [string]::IsNullOrWhiteSpace($deviceFilter)) {
    $devices = @($deviceFilter -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

# Determine execution mode based on what filters were provided
$executionMode = ""
if ($platforms.Count -gt 0 -and $devices.Count -gt 0) {
    $executionMode = "Platform × Device (Cartesian Product)"
} elseif ($platforms.Count -gt 0) {
    $executionMode = "Platform Only (No Device Filter)"
} elseif ($devices.Count -gt 0) {
    $executionMode = "Device Only (No Platform Filter)"
} else {
    Write-Host "##[error]No platforms or devices specified"
    exit 1
}

Write-Host ""
Write-Host "##[section]Generating Execution Matrix"
Write-Host "Execution Mode: $executionMode"
Write-Host "Platforms: $(if ($platforms.Count -gt 0) { $platforms -join ', ' } else { '<any>' })"
Write-Host "Devices: $(if ($devices.Count -gt 0) { $devices -join ', ' } else { '<any>' })"

# Step 3: Generate execution matrix based on filters provided
$matrix = @{}
$validCombinations = 0
$invalidCombinations = 0

if ($platforms.Count -gt 0 -and $devices.Count -eq 0) {
    # Mode 1: Platform only - run on all platforms without device filter
    Write-Host ""
    Write-Host "##[section]Matrix (Platform Only Mode):"
    foreach ($platform in $platforms) {
        $platformLower = $platform.ToLower()

        # Find first online agent matching this platform
        $matchingAgent = $onlineAgents | Where-Object {
            $_.PlatformLower -eq $platformLower
        } | Select-Object -First 1

        if ($matchingAgent) {
            # Create matrix key (sanitized for Azure DevOps)
            $matrixKey = "$($platform)" -replace '[^a-zA-Z0-9_]', '_'

            # Add to matrix with empty device
            $matrix[$matrixKey] = @{
                agentName = $matchingAgent.Name
                platformName = $platform
                deviceName = ""
            }
            $validCombinations++
            Write-Host "  [MATCH] $platform → Agent: $($matchingAgent.Name)"
        }
        else {
            $invalidCombinations++
            Write-Host "  [SKIP] $platform → No matching agent found"
        }
    }
}
elseif ($devices.Count -gt 0 -and $platforms.Count -eq 0) {
    # Mode 2: Device only - run all platforms that have this device
    Write-Host ""
    Write-Host "##[section]Matrix (Device Only Mode):"
    foreach ($device in $devices) {
        $deviceLower = $device.ToLower()

        # Find all unique platforms that have this device
        $platformsWithDevice = $onlineAgents | Where-Object {
            $_.Devices -contains $deviceLower
        } | Select-Object -ExpandProperty Platform -Unique

        foreach ($platform in $platformsWithDevice) {
            # Create matrix key (sanitized for Azure DevOps)
            $matrixKey = "$($platform)_$($device)" -replace '[^a-zA-Z0-9_]', '_'

            # Find first agent matching platform + device
            $matchingAgent = $onlineAgents | Where-Object {
                $_.Platform.ToLower() -eq $platform.ToLower() -and $_.Devices -contains $deviceLower
            } | Select-Object -First 1

            if ($matchingAgent) {
                $matrix[$matrixKey] = @{
                    agentName = $matchingAgent.Name
                    platformName = $platform
                    deviceName = $device
                }
                $validCombinations++
                Write-Host "  [MATCH] $platform × $device → Agent: $($matchingAgent.Name)"
            }
        }
    }
}
else {
    # Mode 3: Both platform and device - cartesian product
    Write-Host ""
    Write-Host "##[section]Matrix (Platform × Device Cartesian Product):"
    foreach ($platform in $platforms) {
        foreach ($device in $devices) {
            $platformLower = $platform.ToLower()
            $deviceLower = $device.ToLower()

            # Find first online agent matching this platform×device combination
            $matchingAgent = $onlineAgents | Where-Object {
                $_.PlatformLower -eq $platformLower -and $_.Devices -contains $deviceLower
            } | Select-Object -First 1

            if ($matchingAgent) {
                # Create matrix key (sanitized for Azure DevOps)
                $matrixKey = "$($platform)_$($device)" -replace '[^a-zA-Z0-9_]', '_'

                # Add to matrix
                $matrix[$matrixKey] = @{
                    agentName = $matchingAgent.Name
                    platformName = $platform
                    deviceName = $device
                }
                $validCombinations++
                Write-Host "  [MATCH] $platform × $device → Agent: $($matchingAgent.Name)"
            }
            else {
                $invalidCombinations++
                Write-Host "  [SKIP] $platform × $device → No matching agent found"
            }
        }
    }
}

Write-Host ""
Write-Host "##[section]Matrix Summary:"
Write-Host "  Valid Combinations: $validCombinations"
Write-Host "  Skipped Combinations: $invalidCombinations"

if ($matrix.Count -eq 0) {
    Write-Host "##[error]No valid combinations found"
    Write-Host "##[error]None of the requested combinations have matching online agents"
    Write-Host "##[error]Requested: Platforms=[$(if ($platforms.Count -gt 0) { $platforms -join ', ' } else { 'none' })] × Devices=[$(if ($devices.Count -gt 0) { $devices -join ', ' } else { 'none' })]"
    exit 1
}

Write-Host "  Matrix Entries: $($matrix.Count)"
Write-Host ""

# Convert to JSON and set output variables
$matrixJson = $matrix | ConvertTo-Json -Compress -Depth 10
Write-Host "##vso[task.setvariable variable=executionMatrix;isOutput=true]$matrixJson"
Write-Host "##vso[task.setvariable variable=foundAgents;isOutput=true]true"
Write-Host "##vso[task.setvariable variable=agentCount;isOutput=true]$($matrix.Count)"

Write-Host "##[section]Generated Matrix JSON:"
Write-Host ($matrix | ConvertTo-Json -Depth 10)