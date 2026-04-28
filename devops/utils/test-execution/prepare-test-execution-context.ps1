# Test Execution Context Preparation Script
# Prepares test execution context and builds pytest arguments
# Parameters:
#   -SuitePath: Test suite path
#   -TestFiles: Comma-separated test files
#   -TestPattern: Test pattern for file discovery
#   -PytestArgs: Base pytest arguments
#   -EnableAgentSelection: Enable agent selection (True/False)
#   -FeatureToTest: Feature being tested
#   -TargetDeviceName: Specific device name if targeting single device
#   -CurrentAgentName: Current agent name (from pipeline variables)

param(
    [string]$SuitePath,
    [string]$TestFiles = "",
    [string]$TestPattern = "test_*.py",
    [string]$PytestArgs = "",
    [string]$EnableAgentSelection = "False",
    [string]$FeatureToTest = "",
    [string]$TargetDeviceName = "",
    [string]$CurrentAgentName = ""
)

Write-Host "Preparing test execution context..."
Write-Host "Suite path: $SuitePath"
Write-Host "Test files: $TestFiles"
Write-Host "Test pattern: $TestPattern"
Write-Host "Pytest args: $PytestArgs"

# Parse test files if provided
$testFilesArray = @()
if ($TestFiles -ne "") {
    $testFilesArray = $TestFiles -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
    Write-Host "Parsed test files: $($testFilesArray -join ', ')"
}

Write-Host "Feature-based testing: $EnableAgentSelection"
Write-Host "Feature to test: $FeatureToTest"
Write-Host "Target specific device: $TargetDeviceName"

# Determine final test pattern
if ($testFilesArray.Count -gt 0 -and $testFilesArray[0] -ne '') {
    # Use specific test files
    $finalPattern = ($testFilesArray -join ' ')
    Write-Host "Using specific test files: $finalPattern"
} else {
    # Use pattern
    $finalPattern = $TestPattern
    Write-Host "Using test pattern: $finalPattern"
}

# No additional pytest arguments needed - tests run with basic pytest command
$additionalArgs = ""

# Set output variables for Azure DevOps
Write-Host "##vso[task.setvariable variable=TEST_PATTERN]$finalPattern"
Write-Host "##vso[task.setvariable variable=FEATURE_ARGS]$additionalArgs"

Write-Host "✅ Test execution context prepared successfully"
Write-Host "   Final test pattern: $finalPattern"