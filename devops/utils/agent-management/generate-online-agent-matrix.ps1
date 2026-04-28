# This script queries Azure DevOps for all online agents in a given pool and outputs a matrix JSON for pipeline use.
# Usage: .\generate-online-agent-matrix.ps1 -Organization "<org>" -Project "<project>" -PoolName "<pool>" -PatEnvVar "AzureDevOpsPAT" -OutputPath "agent-matrix.json"


param(
    [Parameter(Mandatory=$true)]
    [string]$Organization,
    [Parameter(Mandatory=$true)]
    [string]$Project,
    [Parameter(Mandatory=$false)]
    [string]$PoolName = "ASQE-QAMA-General",
    [Parameter(Mandatory=$true)]
    [string]$PatEnvVar,
    [Parameter(Mandatory=$true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"


$pat = [System.Environment]::GetEnvironmentVariable($PatEnvVar)
if (-not $pat) {
    Write-Error "PAT not found in environment variable: $PatEnvVar"
    exit 1
}

$headers = @{ Authorization = ("Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":${pat}"))) }

# Get pool ID by name
$poolUrl = "https://dev.azure.com/$Organization/_apis/distributedtask/pools?api-version=7.1-preview.1"
$pools = Invoke-RestMethod -Uri $poolUrl -Headers $headers -Method Get
$pool = $pools.value | Where-Object { $_.name -eq $PoolName }
if (-not $pool) {
    Write-Error "Agent pool not found: $PoolName"
    exit 1
}
$poolId = $pool.id

# Get agents in pool
$agentsUrl = "https://dev.azure.com/$Organization/_apis/distributedtask/pools/$poolId/agents?api-version=7.1-preview.1"
$agents = Invoke-RestMethod -Uri $agentsUrl -Headers $headers -Method Get

$matrix = @{}

foreach ($agent in $agents.value) {
    if ($agent.status -eq "online") {
        $key = $agent.name.Replace(' ', '_')
        $matrix[$key] = @{ agentName = $agent.name }
    }
}

if ($matrix.Count -eq 0) {
    Write-Warning "No online agents found in pool: $PoolName"
}

# Output as JSON
$matrix | ConvertTo-Json -Depth 5 | Out-File -Encoding UTF8 $OutputPath
Write-Host "Matrix written to $OutputPath"
