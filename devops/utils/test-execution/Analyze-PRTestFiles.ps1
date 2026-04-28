# Analyze-PRTestFiles.ps1
#
# Purpose: Analyzes modified test files in a PR and discovers affected modules
#
# This script:
# - Compares source and target branches to find modified test files
# - Filters for Python test files under tests/hp_app/ in module subdirectories
# - Dynamically discovers affected modules (first directory level under hp_app/)
# - Outputs boolean flags for each discovered module for conditional stage execution
# - Ignores root-level test files (examples only, not executed in PR pipeline)
#
# Outputs (Azure DevOps variables):
# - has_<module>: Boolean flag for each discovered module (e.g., has_pen_control=true)
# - discoveredModules: Comma-separated list of discovered module names
# - hasTestChanges: Boolean indicating if test files were modified

param(
    [Parameter(Mandatory=$false)]
    [string]$SourceBranch = $env:SYSTEM_PULLREQUEST_SOURCEBRANCH,
    
    [Parameter(Mandatory=$false)]
    [string]$TargetBranch = $env:SYSTEM_PULLREQUEST_TARGETBRANCH,
    
    [Parameter(Mandatory=$false)]
    [string]$WorkspaceRoot = "$(Pipeline.Workspace)/s"
)

Write-Host "Analyzing files modified in this PR..."

# Clean branch names (remove refs/heads/ prefix if present)
if ($SourceBranch -and $SourceBranch.StartsWith("refs/heads/")) {
    $SourceBranch = $SourceBranch.Substring(11)
}
if ($TargetBranch -and $TargetBranch.StartsWith("refs/heads/")) {
    $TargetBranch = $TargetBranch.Substring(11)
}

# Default to master if target branch is not available
if ([string]::IsNullOrEmpty($TargetBranch)) {
    $TargetBranch = "master"
}

Write-Host "Source branch: $SourceBranch"
Write-Host "Target branch: $TargetBranch"

# Validate source branch is available
if ([string]::IsNullOrEmpty($SourceBranch)) {
    Write-Host "##vso[task.logissue type=warning]Source branch not available, using current HEAD as fallback"
    $SourceBranch = "HEAD"
}

try {
    # Change to source directory to ensure git commands work correctly
    Write-Host "Changing to source directory: $WorkspaceRoot"
    Set-Location $WorkspaceRoot
    Write-Host "Current directory: $(Get-Location)"
    
    # Use git diff with three-dot syntax to compare merge base
    # This shows only changes in the source branch, not changes in target since branching
    # Azure Pipelines already fetches branches, so we can use origin/ refs directly
    $gitDiffCommand = "git diff --name-only origin/$TargetBranch...HEAD"
    Write-Host "Running command: $gitDiffCommand"
    
    # Execute git command and capture output
    $changedFiles = & git diff --name-only origin/$TargetBranch...HEAD 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "##vso[task.logissue type=warning]Git diff with three-dot syntax failed, trying merge-base approach..."
        Write-Host "Git error output: $changedFiles"
        
        # Find merge base and diff from there
        $mergeBase = & git merge-base origin/$TargetBranch HEAD 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Merge base: $mergeBase"
            $changedFiles = & git diff --name-only $mergeBase HEAD 2>&1
        }
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "##vso[task.logissue type=warning]Merge-base approach failed, trying two-dot syntax..."
            # Fallback to two-dot syntax (direct comparison)
            $changedFiles = & git diff --name-only origin/$TargetBranch..HEAD 2>&1
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "##vso[task.logissue type=warning]All git diff approaches failed, using git status instead..."
                # Last resort: use git status to find changed files
                $changedFiles = & git status --porcelain 2>&1 | ForEach-Object { $_.Substring(3) }
            }
        }
    }
    
    # Debug: Show raw git output
    Write-Host ""
    Write-Host "Raw git diff output:"
    $changedFiles | ForEach-Object { Write-Host "  $_" }
    Write-Host ""
    
    # Ensure changedFiles is an array
    if ($changedFiles -is [string]) {
        $changedFiles = @($changedFiles)
    }
    
    Write-Host "Total changed files: $($changedFiles.Count)"
    
    # Filter for test files under the expected directory structure
    $testBasePath = "tests/hp_app/"
    $relevantFiles = @($changedFiles | Where-Object { 
        $_ -and $_.ToString().StartsWith($testBasePath) -and $_.ToString().EndsWith(".py") 
    })
    
    Write-Host "Relevant test files found: $($relevantFiles.Count)"
    
    if ($relevantFiles.Count -eq 0) {
        Write-Host "No test files modified in expected directory: $testBasePath"
        Write-Host "All changed files:"
        $changedFiles | ForEach-Object { Write-Host "  $_" }
        Write-Host "##vso[task.setvariable variable=hasTestChanges;isOutput=true]false"
        return
    }
}
catch {
    Write-Host "##vso[task.logissue type=error]Failed to analyze file changes: $($_.Exception.Message)"
    Write-Host "##vso[task.setvariable variable=hasTestChanges;isOutput=true]false"
    return
}

# Process all test files and discover modules
Write-Host "Processing $($relevantFiles.Count) modified test file(s)..."

# Track discovered modules and their test files
$moduleTestFiles = @{}
$rootLevelFiles = @()

foreach ($file in $relevantFiles) {
    Write-Host "  Processing: $file"
    
    # Remove base path to get relative path within test structure
    $relativePath = $file.Substring($testBasePath.Length)
    
    # Check if file is at root level (no directory separator)
    $firstSlashIndex = $relativePath.IndexOf("/")
    if ($firstSlashIndex -le 0) {
        # Root-level file - add to warning list but don't process
        $rootLevelFiles += $file
        Write-Host "    Skipping root-level file (examples only): $file"
        continue
    }
    
    # Extract module path (first directory level after hp_app/)
    $modulePath = $relativePath.Substring(0, $firstSlashIndex)
    
    # Extract just the test filename from the relative path
    $testFileName = Split-Path $relativePath -Leaf
    
    # Add to module's test file list
    if (-not $moduleTestFiles.ContainsKey($modulePath)) {
        $moduleTestFiles[$modulePath] = @()
        Write-Host "    Discovered module: $modulePath"
    }
    $moduleTestFiles[$modulePath] += $testFileName
    Write-Host "    Test file: $testFileName"
}

# Show warning if root-level files were found
if ($rootLevelFiles.Count -gt 0) {
    Write-Host "##vso[task.logissue type=warning]Root-level test files detected and ignored (examples only, not executed):"
    foreach ($rootFile in $rootLevelFiles) {
        Write-Host "##vso[task.logissue type=warning]  $rootFile"
    }
}

# Check if any modules were discovered
if ($moduleTestFiles.Count -eq 0) {
    Write-Host "##vso[task.logissue type=warning]No test files found in module subdirectories. Only root-level files were modified."
    Write-Host "##vso[task.setvariable variable=hasTestChanges;isOutput=true]false"
    return
}

# Output module flags and test file lists
$discoveredModules = $moduleTestFiles.Keys | Sort-Object
Write-Host "=========================================="
Write-Host "Discovered Modules: $($discoveredModules.Count)"
Write-Host "=========================================="

foreach ($module in $discoveredModules) {
    # Sanitize module name for variable (replace hyphens/underscores, lowercase)
    $varName = $module.ToLower() -replace '-', '_'
    
    # Get test files for this module
    $testFiles = $moduleTestFiles[$module] | Sort-Object
    $testFilesString = $testFiles -join ','
    
    Write-Host "  ${module}:"
    Write-Host "    has_$varName = true"
    Write-Host "    testfiles_$varName = $testFilesString"
    
    # Output boolean flag for module
    Write-Host "##vso[task.setvariable variable=has_$varName;isOutput=true]true"
    
    # Output comma-separated list of test files for this module
    Write-Host "##vso[task.setvariable variable=testfiles_$varName;isOutput=true]$testFilesString"
}

$discoveredModulesString = $discoveredModules -join ','
Write-Host "=========================================="
Write-Host "Output Variables:"
Write-Host "  discoveredModules: $discoveredModulesString"
Write-Host "  hasTestChanges: true"
Write-Host "=========================================="

Write-Host "##vso[task.setvariable variable=discoveredModules;isOutput=true]$discoveredModulesString"
Write-Host "##vso[task.setvariable variable=hasTestChanges;isOutput=true]true"
