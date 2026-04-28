param(
    [Parameter(Mandatory=$true)]
    [string]$SuitePath,
    
    [Parameter(Mandatory=$true)]
    [string]$PlatformName,
    
    [Parameter(Mandatory=$true)]
    [AllowEmptyString()]
    [string]$DeviceName,
    
    [Parameter(Mandatory=$true)]
    [string]$PytestArgs,
    
    [Parameter(Mandatory=$false)]
    [string]$AdditionalMarkerFilter = "",
    
    [Parameter(Mandatory=$false)]
    [string]$WorkingDirectory = ".",
    
    [Parameter(Mandatory=$false)]
    [string]$SpecificTestFiles = "",
    
    [Parameter(Mandatory=$false)]
    [string]$TestrailCaseIds = ""
)

$DebugPreference = "SilentlyContinue"
$ErrorActionPreference = "Continue"

Write-Host $('=' * 80)
Write-Host "Test Collection for Platform: $PlatformName, Device: $DeviceName"
Write-Host $('=' * 80)

# Determine test path
$isAbsolutePath = [System.IO.Path]::IsPathRooted($SuitePath)

# If WorkingDirectory is not provided or empty, use current directory
if (-not $WorkingDirectory -or $WorkingDirectory -eq "") {
    $WorkingDirectory = "."
}

if ($isAbsolutePath) {
    $testPath = $SuitePath
} else {
    $testPath = Join-Path $WorkingDirectory $SuitePath
}

# Build test targets (specific files or directory)
$testTargets = @()

if ($SpecificTestFiles -ne "") {
    Write-Host "Filtering to specific test files: $SpecificTestFiles"
    $fileList = $SpecificTestFiles -split ','
    foreach ($fileName in $fileList) {
        $fileName = $fileName.Trim()
        if ($fileName) {
            $fullPath = Join-Path $testPath $fileName
            if (Test-Path $fullPath) {
                $testTargets += "`"$fullPath`""
                Write-Host "  [OK] Will collect from: $fileName"
            } else {
                Write-Warning "  [SKIP] File not found (skipping): $fileName"
            }
        }
    }
    
    if ($testTargets.Count -eq 0) {
        Write-Error "[EXIT REASON] No valid test files found from the specific files list. Exiting with code 1."
    }
} else {
    Write-Host "Collecting from all tests in directory: $testPath"
    $testTargets = @("`"$testPath`"")
}

# Build automatic marker filter from matrix variables
$platform = $PlatformName
$device = $DeviceName

# Build marker filter - only include device if it's not empty
if ($device -ne "") {
    $markerFilter = "platform_$platform and device_$device"
} else {
    $markerFilter = "platform_$platform"
}

# Add additional marker filter if specified
if ($AdditionalMarkerFilter -ne "") {
    $markerFilter = "($markerFilter) and ($AdditionalMarkerFilter)"
}

# Build collect-only command
$collectCmd = "python -m pytest --collect-only -q"

# Disable warnings only for unknown marks (platform_* and device_* are dynamically created)
$collectCmd += " -W ignore::pytest.PytestUnknownMarkWarning"

# Add pytest args from user
if ($PytestArgs -ne "") {
    $collectCmd += " $PytestArgs"
}

# Add automatic marker filter
$collectCmd += " -m `"$markerFilter`""

# Add TestRail case IDs if provided
if ($TestrailCaseIds -ne "") {
    $collectCmd += " --testrail-case-ids `"$TestrailCaseIds`""
}

# Add test targets (files or directory)
$collectCmd += " " + ($testTargets -join ' ')

Write-Host "Auto-generated marker filter: -m `"$markerFilter`""
Write-Host "Collection command: $collectCmd"
Write-Host ""

# Run collection and capture output
$collectionOutput = Invoke-Expression $collectCmd 2>&1 | Out-String

# Parse and display tests grouped by file
Write-Host "Tests to be executed:"
Write-Host ""

$currentFile = ""

$testCount = 0
$fileTestCount = 0
$fileSkippedCount = 0
$inFile = $false
$skippedTests = @{}
$fileTestMap = @{}
$currentFile = ""

foreach ($line in $collectionOutput -split "`n") {
    $line = $line.Trim()
    # Match test file pattern: <Module path/to/file.py>
    if ($line -match '<Module (.+\.py)>') {
        if ($currentFile -ne "") {
            if ($fileTestCount -gt 0) {
                Write-Host "    ($fileTestCount test(s))"
                Write-Host ""
            } elseif ($fileSkippedCount -gt 0) {
                Write-Host "    (all tests skipped: $fileSkippedCount)"
                Write-Host ""
            } else {
                Write-Host "    (0 test(s))"
                Write-Host ""
            }
        }
        $currentFile = $matches[1]
        $fileTestCount = 0
        $fileSkippedCount = 0
        Write-Host "  File: $currentFile"
    }
    # Match test function pattern: <Function test_name>
    elseif ($line -match '<Function (test_\w+)>') {
        $testName = $matches[1]
        Write-Host "    - $testName"
        $testCount++
        $fileTestCount++
    }
    # Match skipped test pattern: <Skipped test_name>
    elseif ($line -match '<Skipped (test_\w+)>') {
        $testName = $matches[1]
        Write-Host "    - $testName (skipped)"
        $fileSkippedCount++
        if (-not $skippedTests.ContainsKey($currentFile)) {
            $skippedTests[$currentFile] = @()
        }
        $skippedTests[$currentFile] += $testName
    }
}

if ($currentFile -ne "") {
    if ($fileTestCount -gt 0) {
        Write-Host "    ($fileTestCount test(s))"
        Write-Host ""
    } elseif ($fileSkippedCount -gt 0) {
        Write-Host "    (all tests skipped: $fileSkippedCount)"
        Write-Host ""
    } else {
        Write-Host "    (0 test(s))"
        Write-Host ""
    }
}


Write-Host $('-' * 80)
Write-Host "Total tests collected: $testCount"
Write-Host $('-' * 80)

Write-Host ""



if ($testCount -eq 0) {
    Write-Host "[EXIT REASON] No tests were collected for this configuration. Exiting with code 0."
    exit 0
}

# Show execution command that will be run
$execCmd = "python -m pytest"
if ($PytestArgs -ne "") {
    $execCmd += " $PytestArgs"
}
$execCmd += " -m `"$markerFilter`""
if ($TestrailCaseIds -ne "") {
    $execCmd += " --testrail-case-ids `"$TestrailCaseIds`""
}
$execCmd += " --junit-xml=`$(Agent.TempDirectory)/test-results-$PlatformName-$DeviceName.xml"
$execCmd += " --test-target localhost"
$execCmd += " " + ($testTargets -join ' ')


Write-Host "Execution command (next step):"
Write-Host $execCmd
Write-Host $('=' * 80)

# Always exit 0 unless a true error occurred above
Write-Host "[EXIT REASON] Test collection completed successfully. Exiting with code 0."
exit 0
