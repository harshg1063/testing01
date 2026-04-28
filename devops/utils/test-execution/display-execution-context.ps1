param(
    [Parameter(Mandatory=$true)]
    [string]$PlatformName,
    
    [Parameter(Mandatory=$true)]
    [AllowEmptyString()]
    [string]$DeviceName,
    
    [Parameter(Mandatory=$true)]
    [string]$AgentPlatform,
    
    [Parameter(Mandatory=$true)]
    [string]$AgentName,
    
    [Parameter(Mandatory=$true)]
    [string]$ActualAgentName,
    
    [Parameter(Mandatory=$true)]
    [string]$ActualMachineName
)

$DebugPreference = "SilentlyContinue"

Write-Host "="*80
Write-Host "Marker-Based Test Execution"
Write-Host "="*80
Write-Host "Required Platform: $PlatformName"
Write-Host "Required Device: $DeviceName"
Write-Host "Target Agent Platform: $AgentPlatform"
Write-Host "Target Agent Name: $AgentName"
Write-Host "Actual Agent: $ActualAgentName"
Write-Host "Actual Machine: $ActualMachineName"
Write-Host "Machine Hostname: $env:COMPUTERNAME"
Write-Host "IP Address: $((Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike '127.*'} | Select-Object -First 1).IPAddress)"

# Retrieve TeamViewer ID
try {
    $teamViewerId = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\WOW6432Node\TeamViewer' -Name ClientID -ErrorAction SilentlyContinue).ClientID
    if (-not $teamViewerId) {
        $teamViewerId = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\TeamViewer' -Name ClientID -ErrorAction SilentlyContinue).ClientID
    }
    if ($teamViewerId) {
        Write-Host "TeamViewer ID: $teamViewerId"
    } else {
        Write-Host "TeamViewer ID: Not found"
    }
} catch {
    Write-Host "TeamViewer ID: Unable to retrieve"
}

Write-Host ""
Write-Host "NOTE: Agent capabilities were validated during discovery phase"
Write-Host "      This job only executes if agent has required capabilities"
Write-Host "="*80
