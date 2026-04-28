#!/usr/bin/env pwsh

<#
.SYNOPSIS
    Sets execution context information for Azure DevOps pipeline display
    
.DESCRIPTION
    This script determines and displays the execution context (Specific Device, Matrix Mode, or General Pool)
    and sets pipeline variables for use in subsequent steps.
    
.PARAMETER TargetDeviceName
    The target device name if running in specific device mode
    
.PARAMETER FeatureToTest
    The feature being tested if running in matrix mode
    
.PARAMETER SuitePath
    The test suite path being executed
    
.PARAMETER CurrentAgentName
    The current agent name (for matrix mode)
    
.EXAMPLE
    ./set-execution-context.ps1 -TargetDeviceName "HP EliteBook" -SuitePath "audio"
    ./set-execution-context.ps1 -FeatureToTest "Audio Control" -SuitePath "audio" -CurrentAgentName "Agent1"
#>

param(
    [Parameter(Mandatory = $false)]
    [string]$TargetDeviceName = "",
    
    [Parameter(Mandatory = $false)]
    [string]$FeatureToTest = "",
    
    [Parameter(Mandatory = $true)]
    [string]$SuitePath,
    
    [Parameter(Mandatory = $false)]
    [string]$TestFiles = "",
    
    [Parameter(Mandatory = $false)]
    [string]$CurrentAgentName = ""
)

$context = ""

if ($TargetDeviceName -ne "") {
    $context = "Specific Device: $TargetDeviceName"
} elseif ($FeatureToTest -ne "") {
    if ($CurrentAgentName -ne "") {
        $context = "$FeatureToTest Matrix Mode - Agent: $CurrentAgentName"
    } else {
        $context = "$FeatureToTest Matrix Mode"
    }
} else {
    $context = "General Pool Mode"
}

Write-Host "##[section]Execution Context: $context"
Write-Host "##[section]Test Suite: $SuitePath"
if ($TestFiles -ne "") {
    Write-Host "##[section]Test Files: $TestFiles"
}
Write-Host "##vso[task.setvariable variable=executionContext]$context"