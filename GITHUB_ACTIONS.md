# GitHub Actions Build System

This repository uses GitHub Actions to automatically build PyInstaller executables for multiple platforms when GitHub releases are created.

## Workflows

### 1. `ci.yml` - Continuous Integration
**Triggers:** Push to main branch and pull requests
**Purpose:** Fast testing and validation for development

**What it does:**
- Runs linting with flake8
- Tests application startup
- Validates database schema
- Runs security scans (Bandit and Safety)

### 2. `build-release.yml` - Comprehensive Release Pipeline
**Triggers:** Creating a GitHub release
**Purpose:** Full testing, validation, and release distribution

**What it does:**
- Tests database integrity and validates data exists
- Validates application startup and database queries
- Builds executables for Linux, Windows, and macOS
- Verifies executable properties and brief runtime tests
- Uploads executables as GitHub artifacts (30-day retention)
- Automatically attaches executables to GitHub releases
- Generates detailed build information and usage instructions

**How to use:**
1. Create a new release in GitHub (Releases → Create a new release)
2. Choose a tag (e.g., `v1.0.0`)
3. GitHub Actions will automatically:
   - Validate the codebase and database
   - Build and test executables for all platforms
   - Attach executables to the release
   - Generate build documentation
4. Users can download directly from the release page

## File Structure

```
.github/
└── workflows/
    ├── ci.yml              # Continuous integration (testing)
    └── build-release.yml   # Comprehensive release pipeline
```

## Platform-Specific Executables

| Platform | Executable Name | Notes |
|----------|----------------|-------|
| Linux | `philmont-trek-selector-linux` | Requires `chmod +x` to make executable |
| Windows | `philmont-trek-selector-windows.exe` | Double-click to run |
| macOS | `philmont-trek-selector-macos` | May need to allow in Security settings |

## Usage for End Users

### From GitHub Releases:
1. Go to the Releases page
2. Find the latest release
3. Download the executable for your platform from Assets
4. Run the executable

### Running the Executable:
1. **Linux/macOS**: 
   ```bash
   chmod +x philmont-trek-selector-*
   ./philmont-trek-selector-*
   ```

2. **Windows**: 
   Double-click `philmont-trek-selector-windows.exe`

3. **All Platforms**: 
   Open browser to `http://127.0.0.1:5002`

## Development Notes

### Modifying the Build Process:
- Edit the YAML files in `.github/workflows/`
- Test changes in a fork or feature branch first
- The build process includes database verification and basic app testing

### Adding New Platforms:
- Modify the `matrix` section in the workflow files
- Add appropriate `path_separator` for the new platform
- Update executable naming convention

### Build Dependencies:
- Python 3.11
- All packages from `requirements.txt`
- PyInstaller (installed during build)
- Database file (`philmont_selection.db`)
- Templates directory

The automated build system ensures that every commit to main produces tested, ready-to-distribute executables for all major platforms.