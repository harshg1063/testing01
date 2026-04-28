<#
.SYNOPSIS
    Aggregates JUnit XML test results and displays a comprehensive summary.

.DESCRIPTION
    This script parses JUnit XML test result files from a specified directory,
    aggregates the results by test suite, and displays a detailed summary including:
    - Test results grouped by suite (with platform/device information)
    - Individual test case status (Passed/Failed/Skipped)
    - Overall summary with total counts
    - Sets pipeline result based on test outcomes

.PARAMETER TestResultsPath
    The path to the directory containing JUnit XML test result files.
    Defaults to "$(Pipeline.Workspace)/TestResults" for Azure Pipelines.

.EXAMPLE
    .\Aggregate-TestResults.ps1 -TestResultsPath "C:\TestResults"

.NOTES
    Author: ASQE-QAMA Team
    Purpose: Daily test execution result aggregation
    Azure DevOps: Sets pipeline variables and task completion status
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$TestResultsPath = "$(Pipeline.Workspace)/TestResults"
)

$ErrorActionPreference = "Continue"

Write-Host "="*80
Write-Host "DAILY TEST EXECUTION SUMMARY"
Write-Host "="*80
Write-Host ""

# Find all JUnit XML files
$testResultFiles = Get-ChildItem -Path $TestResultsPath -Filter "*.xml" -Recurse -ErrorAction SilentlyContinue

if (-not $testResultFiles -or $testResultFiles.Count -eq 0) {
    Write-Host "No test result files found. Tests may not have executed."
    Write-Host "Search path: $TestResultsPath"
    exit 0
}

Write-Host "Found $($testResultFiles.Count) test result file(s)"
Write-Host ""

# Parse JUnit XML files and aggregate results
$totalTests = 0
$totalPassed = 0
$totalFailed = 0
$totalSkipped = 0
$testSuites = @{}

foreach ($file in $testResultFiles) {
    Write-Host "Processing: $($file.Name)"
    
    try {
        [xml]$xmlContent = Get-Content $file.FullName
        
        # JUnit XML can have different structures
        $testsuiteNodes = $xmlContent.SelectNodes("//testsuite")
        
        foreach ($testsuite in $testsuiteNodes) {
            $suiteName = $testsuite.name
            if (-not $suiteName) { $suiteName = $file.BaseName }
            
            # Extract platform/device from file name
            # Format: test-results-<platform>-<device>.xml
            if ($file.Name -match 'test-results-([^-]+)-(.+)\.xml') {
                $platform = $matches[1]
                $device = $matches[2]
                $suiteKey = "$suiteName [$platform × $device]"
            } else {
                $suiteKey = $suiteName
            }
            
            if (-not $testSuites.ContainsKey($suiteKey)) {
                $testSuites[$suiteKey] = @{
                    Tests = @()
                    Passed = 0
                    Failed = 0
                    Skipped = 0
                }
            }
            
            # Process test cases
            $testcases = $testsuite.SelectNodes(".//testcase")
            foreach ($testcase in $testcases) {
                $testName = $testcase.name
                $className = $testcase.classname
                
                # Determine test status
                $status = "Passed"
                $message = ""
                
                if ($testcase.failure) {
                    $status = "Failed"
                    $message = $testcase.failure.message
                    $testSuites[$suiteKey].Failed++
                    $totalFailed++
                }
                elseif ($testcase.error) {
                    $status = "Failed"
                    $message = $testcase.error.message
                    $testSuites[$suiteKey].Failed++
                    $totalFailed++
                }
                elseif ($testcase.skipped) {
                    $status = "Skipped"
                    $message = $testcase.skipped.message
                    $testSuites[$suiteKey].Skipped++
                    $totalSkipped++
                }
                else {
                    $testSuites[$suiteKey].Passed++
                    $totalPassed++
                }
                
                $totalTests++
                
                $testSuites[$suiteKey].Tests += @{
                    Name = $testName
                    ClassName = $className
                    Status = $status
                    Message = $message
                }
            }
        }
    }
    catch {
        Write-Warning "Failed to parse $($file.Name): $_"
    }
}

# Display results by test suite
Write-Host ""
Write-Host "="*80
Write-Host "TEST RESULTS BY SUITE"
Write-Host "="*80
Write-Host ""

foreach ($suiteKey in ($testSuites.Keys | Sort-Object)) {
    $suite = $testSuites[$suiteKey]
    $suiteTotal = $suite.Passed + $suite.Failed + $suite.Skipped
    
    Write-Host "Suite: $suiteKey"
    Write-Host "  Total: $suiteTotal | Passed: $($suite.Passed) | Failed: $($suite.Failed) | Skipped: $($suite.Skipped)"
    Write-Host ""
    
    # Group tests by status
    $passedTests = $suite.Tests | Where-Object { $_.Status -eq "Passed" }
    $failedTests = $suite.Tests | Where-Object { $_.Status -eq "Failed" }
    $skippedTests = $suite.Tests | Where-Object { $_.Status -eq "Skipped" }
    
    if ($passedTests) {
        Write-Host "  [PASSED] ($($passedTests.Count) tests):"
        foreach ($test in $passedTests) {
            $displayName = if ($test.ClassName) { "$($test.ClassName)::$($test.Name)" } else { $test.Name }
            Write-Host "    [OK] $displayName" -ForegroundColor Green
        }
        Write-Host ""
    }
    
    if ($failedTests) {
        Write-Host "  [FAILED] ($($failedTests.Count) tests):" -ForegroundColor Red
        foreach ($test in $failedTests) {
            $displayName = if ($test.ClassName) { "$($test.ClassName)::$($test.Name)" } else { $test.Name }
            Write-Host "    [FAIL] $displayName" -ForegroundColor Red
            if ($test.Message) {
                Write-Host "      Error: $($test.Message)" -ForegroundColor Yellow
            }
        }
        Write-Host ""
    }
    
    if ($skippedTests) {
        Write-Host "  [SKIPPED] ($($skippedTests.Count) tests):"
        foreach ($test in $skippedTests) {
            $displayName = if ($test.ClassName) { "$($test.ClassName)::$($test.Name)" } else { $test.Name }
            Write-Host "    [SKIP] $displayName" -ForegroundColor Gray
            if ($test.Message) {
                Write-Host "      Reason: $($test.Message)" -ForegroundColor Gray
            }
        }
        Write-Host ""
    }
}

# Display overall summary
Write-Host "="*80
Write-Host "OVERALL SUMMARY"
Write-Host "="*80
Write-Host "Total Test Suites: $($testSuites.Count)"
Write-Host "Total Tests: $totalTests"
Write-Host "  Passed:  $totalPassed" -ForegroundColor Green
Write-Host "  Failed:  $totalFailed" -ForegroundColor $(if ($totalFailed -gt 0) { "Red" } else { "White" })
Write-Host "  Skipped: $totalSkipped" -ForegroundColor Gray
Write-Host "="*80

# Set pipeline result
if ($totalFailed -gt 0) {
    Write-Host ""
    Write-Host "##vso[task.logissue type=error]$totalFailed test(s) failed"
    Write-Host "##vso[task.complete result=Failed;]Tests failed"
    exit 1
}
elseif ($totalTests -eq 0) {
    Write-Host ""
    Write-Host "##vso[task.logissue type=warning]No tests were executed"
    exit 0
}
else {
    Write-Host ""
    Write-Host "All tests passed!" -ForegroundColor Green
    exit 0
}
