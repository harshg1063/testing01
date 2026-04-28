param(
    [Parameter(Mandatory=$true)]
    [string]$features
)

Write-Output "Starting agent discovery for features: $features"

# Check if Python is available
$pythonCmd = "python"
try {
    $pythonVersion = & $pythonCmd --version 2>&1
    Write-Output "Python version: $pythonVersion"
} catch {
    Write-Error "Python not found. Please ensure Python is installed and in PATH."
    exit 1
}

# Check if agent-selector.py exists
$scriptPath = Join-Path $PSScriptRoot "agent-selector.py"
if (-not (Test-Path $scriptPath)) {
    Write-Error "agent-selector.py not found at: $scriptPath"
    exit 1
}

Write-Output "Running Python script: $scriptPath"

# Execute the Python script
try {
    $pythonResult = & $pythonCmd $scriptPath --feature $features --json 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Python script had warnings but returned results"
    }
    Write-Output "Python script output: $pythonResult"
} catch {
    Write-Error "Failed to execute Python script: $($_.Exception.Message)"
    exit 1
}

# Parse the result as JSON
try {
    $agents = $pythonResult | ConvertFrom-Json
    Write-Output "Found $($agents.Count) agents"
} catch {
    Write-Error "Failed to parse JSON result: $($_.Exception.Message)"
    Write-Error "Raw result: $pythonResult"
    exit 1
}

# Create matrix structure - deduplicate to get only first available agent per unique name
$matrix = @{}
$uniqueAgents = @{}
$index = 0

foreach ($agent in $agents.available_agents) {
    # Skip if we've already added this agent name
    if ($uniqueAgents.ContainsKey($agent)) {
        Write-Output "Skipping duplicate agent: $agent"
        continue
    }
    
    $index++
    $uniqueAgents[$agent] = $true
    
    # Use agent name as matrix key for cleaner job names (replace spaces/dots with underscores)
    $matrixKey = $agent -replace '[^a-zA-Z0-9]', '_'
    $matrix[$matrixKey] = @{
        "agentName" = $agent
        "deviceName" = $agent
    }
    
    Write-Output "Added agent to matrix: $agent"
}

# Convert to JSON and output
$matrixJson = $matrix | ConvertTo-Json -Compress
$hasAgents = if ($index -gt 0) { "true" } else { "false" }

Write-Output "##vso[task.setVariable variable=agentMatrix;isOutput=true]$matrixJson"
Write-Output "##vso[task.setVariable variable=foundAgents;isOutput=true]$hasAgents"
Write-Output "##vso[task.setVariable variable=agentCount;isOutput=true]$index"
Write-Output "Agent matrix created successfully with $index agents"