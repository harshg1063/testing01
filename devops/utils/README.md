# DevOps Utilities

This directory contains utilities and scripts for Azure DevOps pipeline automation, organized by function.

## 📁 Directory Structure

```
utils/
├── agent-management/          # Agent discovery and selection
├── app-installation/          # myHP application installation
├── device-data/              # Device capability databases
├── test-execution/           # Test execution utilities
└── shared-test-variables.yml # Centralized pipeline configuration
```

---

## 🤖 agent-management/

**Purpose:** Discover and select appropriate agents for test execution based on device capabilities.

### Files:
- **`discover-agents-for-feature.ps1`** - Discovers agents supporting a specific feature
  - Used in matrix execution mode
  - Creates deduplicated agent matrix
  - Sets pipeline variables: `agentMatrix`, `foundAgents`, `agentCount`

- **`agent-selector.py`** - Python utility for matching features to agents
  - Queries device capability database
  - Returns JSON output with agent information
  - Used by discover-agents-for-feature.ps1

- **`agent-pool.txt`** - Agent pool database
  - Maps agent names to their capabilities
  - Format: `AgentName,Platform,Capability1,Capability2,...`

### Usage Example:
```yaml
- task: PowerShell@2
  name: DiscoverAgents
  inputs:
    filePath: '$(Build.Repository.LocalPath)/devops/utils/agent-management/discover-agents-for-feature.ps1'
    arguments: '-features "Audio Control"'
```

---

## 📦 app-installation/

**Purpose:** Automated myHP application installation with version checking and certificate management.

### Files:
- **`get-target-build-version.ps1`** - Retrieves target build from Azure DevOps API
- **`check-installation-needed.ps1`** - Verifies if installation is needed
- **`check-package-downloaded.ps1`** - Checks local package cache
- **`install-signing-certificate.ps1`** - Installs code signing certificate
- **`remove-old-myhp.ps1`** - Removes existing myHP installation
- **`install-myhp-package.ps1`** - Installs MSIX bundle package
- **`README.md`** - Detailed documentation for all scripts

### Used By:
- `devops/templates/job templates/install-myhp-steps.yml`

---

## 📊 device-data/

**Purpose:** Device capability databases and device information management.

### Files:
- **`device-list-parser.py`** - Parses device capability matrices
  - Searches for devices supporting specific features
  - Supports consumer and commercial databases
  - Used by agent-selector.py

- **`HPX Release Matrix for Consumer_20241125.xlsx`** - Consumer device database
- **`myHP_HPX Release Matrix for CMIT.xlsx`** - Commercial device database

### Usage Example:
```bash
python device-list-parser.py --search "Audio Control" --consumer
```

---

## 🧪 test-execution/

**Purpose:** Utilities for test execution setup and context management.

### Files:
- **`start-appium-server.ps1`** - Starts Appium server for mobile testing
  - Configures port and device settings
  - Used before mobile test execution

- **`set-execution-context.ps1`** - Displays execution context information
  - Shows test environment details
  - Helps with debugging pipeline issues

- **`prepare-test-execution-context.ps1`** - Prepares test execution environment
  - Sets up test context variables
  - Configures test parameters

- **`validate-pipeline-parameters.ps1`** - Validates pipeline parameter combinations
  - Checks matrix mode vs single device mode settings
  - Provides clear feedback on execution mode
  - Used in pipeline parameter validation jobs

### Usage Example:
```yaml
- task: PowerShell@2
  displayName: 'Start Appium Server'
  inputs:
    filePath: '$(Build.Repository.LocalPath)/devops/utils/test-execution/start-appium-server.ps1'
    arguments: '-port 4723'
```

---

## ⚙️ shared-test-variables.yml

**Purpose:** Centralized configuration for ALL test pipelines.

### Contains:
- Test suite paths
- Agent pool configuration
- Default test parameters
- Utility script paths
- Build configuration

### Usage:
Include in any pipeline that runs tests:

```yaml
variables:
- template: utils/shared-test-variables.yml
```

### When to Update:
- Project structure changes
- Agent pool name changes
- Default configurations need adjustment
- New utility scripts are added

---

##  Related Documentation

- **Pipeline Templates:** `devops/templates/`
- **Job Templates:** `devops/templates/job templates/`
- **App Installation:** `devops/utils/app-installation/README.md`
- **Main Pipeline Documentation:** `devops/PIPELINE_DOCUMENTATION.md`

---

## 🤝 Contributing

When adding new utilities:

1. **Place in appropriate folder** based on function
2. **Update this README** with script documentation
3. **Update shared-test-variables.yml** if adding new script paths
4. **Add inline documentation** in scripts (comments explaining purpose, parameters, outputs)
5. **Consider creating a README** in the subfolder for complex utilities

---

## 💡 Design Principles

- **Group by function, not by technology** - Easier to find related scripts
- **Centralize configuration** - Use shared-test-variables.yml
- **Document thoroughly** - Every script should have clear documentation
- **Reusability** - Scripts should be reusable across multiple pipelines
- **Maintainability** - Keep scripts focused on single responsibilities
