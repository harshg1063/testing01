# App Installation Utility Scripts

This directory contains PowerShell scripts for managing myHP application installation in Azure DevOps pipelines.

## Scripts

### 1. get-target-build-version.ps1
**Purpose:** Retrieves the target build and version information from Azure DevOps Build API.

**Parameters:**
- `organization` - Azure DevOps organization URL
- `project` - Project ID
- `pipelineId` - Pipeline definition ID
- `providedBuildId` - (Optional) Specific build ID to use
- `buildVersionToDownload` - Strategy: 'latest', 'latestFromBranch', or 'specific'
- `accessToken` - Azure DevOps access token

**Output Variables:**
- `TargetVersion` - The build number/version to install
- `ActualBuildId` - The build ID that will be used

---

### 2. check-installation-needed.ps1
**Purpose:** Determines if myHP needs to be installed by checking the current version.

**Parameters:**
- `targetVersion` - The version to check against

**Output Variables:**
- `NeedsInstall` - 'true' if installation needed, 'false' otherwise

**Logic:**
- Checks if myHP is installed for the current user
- Verifies the installed version matches target version
- Confirms application files actually exist at the install location

---

### 3. check-package-downloaded.ps1
**Purpose:** Checks if the installation package has already been downloaded and extracted.

**Parameters:**
- `artifactsDirectory` - Azure DevOps artifacts directory

**Output Variables:**
- `NeedsDownload` - 'true' if download needed, 'false' if already cached

**Benefits:**
- Avoids redundant downloads
- Speeds up pipeline execution when package is cached

---

### 4. install-signing-certificate.ps1
**Purpose:** Installs the code signing certificate required for myHP installation.

**Parameters:**
- `artifactsDirectory` - Azure DevOps artifacts directory

**Actions:**
- Finds the .cer file in the extracted package
- Imports to LocalMachine\Root certificate store
- Imports to LocalMachine\TrustedPeople certificate store

---

### 5. remove-old-myhp.ps1
**Purpose:** Removes any existing myHP installation before installing the new version.

**Parameters:** None

**Actions:**
- Searches for installed myHP package
- Removes it if found using Remove-AppxPackage

---

### 6. install-myhp-package.ps1
**Purpose:** Installs the myHP MSIX bundle package.

**Parameters:**
- `artifactsDirectory` - Azure DevOps artifacts directory

**Actions:**
- Locates the *_x64.msixbundle file
- Installs using Add-AppxPackage with force flags
- Forces application shutdown and allows version downgrade if needed

---

## Usage in Templates

These scripts are used by `install-myhp-steps.yml` template. Example:

```yaml
- task: PowerShell@2
  displayName: 'Get Target Build and Version'
  name: GetTargetVersion
  inputs:
    targetType: 'filePath'
    filePath: '$(Build.Repository.LocalPath)/devops/utils/app-installation/get-target-build-version.ps1'
    arguments: >-
      -organization "$(System.TeamFoundationCollectionUri)"
      -project "${{ parameters.projectId }}"
      -pipelineId "${{ parameters.pipelineId }}"
      -providedBuildId "${{ parameters.buildId }}"
      -buildVersionToDownload "${{ parameters.buildVersionToDownload }}"
      -accessToken "$(System.AccessToken)"
```

## Installation Flow

1. **Get Target Version** - Determines which build to install
2. **Check Installation** - Skips if correct version already installed
3. **Check Download** - Skips download if package already cached
4. **Download Package** - (Conditional) Downloads from Azure DevOps artifacts
5. **Extract Package** - (Conditional) Extracts the ZIP archive
6. **Install Certificate** - Installs code signing certificate
7. **Remove Old Version** - Cleans up previous installation
8. **Install Package** - Installs the new MSIX bundle