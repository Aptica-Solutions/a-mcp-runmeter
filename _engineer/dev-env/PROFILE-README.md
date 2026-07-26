# ultra-profile

A portable, no-admin-required PowerShell development environment that works identically on macOS and Windows. All functions live in a single file; the machine profile is a thin loader that finds and dot-sources it.

## Quick Start

### Bootstrap a new machine (run once)

```powershell
pwsh -NoProfile ./bootstrap-profile.ps1
```

This writes a thin loader to `$PROFILE` that finds and dot-sources `profile.ps1` from this directory. On Windows it also sets `$env:ULTRA_PROFILE` as a persistent user env var.

### Launch VS Code with dev tooling

```powershell
pwsh -NoProfile ./launch-code.ps1 /path/to/workspace.code-workspace
```

Works on macOS (Homebrew) and Windows (Scoop) — OS detected automatically.

**Options:**
- `-PortableUserData` — Isolated VS Code config (macOS: `~/.vscode-portable-user-data`, Windows: Scoop data dir)
- `-DevRoot /path` — Default directory for interactive terminals

## File Structure

```
ultra-profile/
├── functions.ps1            ← All functions — edit this to add new ones
├── profile.ps1              ← Master loader (dot-sources functions.ps1)
├── bootstrap-profile.ps1    ← One-shot machine setup script
├── launch-code.ps1          ← VS Code launcher (macOS + Windows)
├── vscode-settings.shared.json  ← VS Code terminal profile definitions
└── ../workbench/            ← Experiments / scratch (gitignored)
```

The three legacy layer files (`pwsh-dev-tools.ps1`, `pwsh-dev-interactive.ps1`, `pwsh-dev-heavy.ps1`) are kept as one-line stubs that forward to `functions.ps1` for backward compatibility with any existing `$env:DEV_TOOLS` references.

## Available Functions

On every load, `Show-ProfileHelp` prints the full function list. Run it again any time:

```powershell
Show-ProfileHelp
```

| Platform | Function | Usage |
|----------|----------|-------|
| ANY | `..` / `...` / `....` | Navigate up 1–3 levels |
| WIN | `Expand-Msi` | Extract MSI without installing |
| WIN | `Update-AWSClipboardRedirection` | Fix clipboard for AWS WorkSpaces PCoIP `[-RestartNow]` |
| WIN | `Unlock-DevSecretStore` | Unlock SecretManagement vault interactively |
| WIN | `Set-Secrets` | Store OP token in Windows SecretManagement |
| WIN | `Invoke-ScoopToolset` | Install/update Scoop dev toolset `[-DryRun]` |
| MAC | `Invoke-BrewToolset` | Install/update Homebrew dev toolset `[-DryRun]` |
| ANY | `Connect-OpSignin` | Sign in to 1Password CLI via stored token |
| ANY | `New-GitHubRepo` | Init cwd and push to a new private GitHub repo |
| ANY | `Invoke-AdoRepoSync` | Generate/apply ADO updates from current repo `-ParentId <id> [-BaseRef <ref>] [-Apply]` |
| ANY | `New-RepoFromTemplate` | Clone or apply `<your-org>/repo-template` |
| ANY | `Show-ProfileHelp` | Show this list |

## Adding a Function

Edit `functions.ps1` — it's the only file you need to touch. Add a new entry to `$script:_Manifest` near the bottom so it shows up in `Show-ProfileHelp`:

```powershell
[PSCustomObject]@{ P = 'ANY'; Name = 'My-NewFunction'; Note = 'What it does and key params' }
```

Guard platform-specific code with `Test-IsWindows`:

```powershell
function My-NewFunction {
    [CmdletBinding()]
    param()
    if (-not (Test-IsWindows)) { throw 'Windows-only.' }
    # ...
}
```

## VS Code Terminal Profiles

After launching via a launcher script, two terminal profiles are available:

| Profile | What loads |
|---------|-----------|
| `pwsh (clean)` | Bare PowerShell, no extras |
| `pwsh (dev)` | All functions from `functions.ps1` |

## Package Management

**macOS:**
```powershell
Invoke-BrewToolset          # install/update all packages
Invoke-BrewToolset -DryRun  # preview only
```

**Windows:**
```powershell
Invoke-ScoopToolset          # install/update all packages
Invoke-ScoopToolset -DryRun  # preview only
```

Default toolset: PowerShell 7+, .NET SDK 9.0, Git, GitHub CLI (`gh`), Node.js LTS, Python 3, 1Password CLI.
Customize by editing `Get-DesiredScoopPackages` or `Get-DesiredBrewToolset` in `functions.ps1`.

## Repo Helpers

```powershell
# Create a new repo from the template
New-RepoFromTemplate -Name my-project -Destination ~/projects
New-RepoFromTemplate -Name my-project -Destination ~/projects -FreshHistory

# Apply template files to an existing repo
New-RepoFromTemplate -Apply ~/projects/legacy-repo
New-RepoFromTemplate -Apply ~/projects/legacy-repo -Force   # overwrite existing files

# Push cwd to a new private GitHub repo
New-GitHubRepo

# From any source repo: preview ADO updates for an existing parent/root item
Invoke-AdoRepoSync -ParentId 2505

# Apply the generated updates after reviewing the preview
Invoke-AdoRepoSync -ParentId 2505 -Apply

# Optionally compare only work changed since a ref
Invoke-AdoRepoSync -ParentId 2505 -BaseRef origin/main
```

`Invoke-AdoRepoSync` is a thin wrapper around `ia-ado-pbi-automation/ado_repo_sync.py`.
Set `ADO_PBI_AUTOMATION_REPO` if the automation repo is not in one of the default `~/foundry` / OneDrive locations.

## Secrets & 1Password

1Password CLI is auto-signed-in on profile load via `Connect-OpSignin`. It reads the service account token from:
- **macOS:** Keychain (`op_service_account_token`)
- **Windows:** SecretManagement (`OP_SERVICE_ACCOUNT_TOKEN`)

To store the token on Windows:
```powershell
Set-Secrets
```

## Cross-Platform Path Override

Set `$env:ULTRA_PROFILE` to point to this directory on any machine where the auto-detected OneDrive path differs:

```powershell
# In your system/user environment variables:
ULTRA_PROFILE = /custom/path/to/ultra-profile
```

## No Admin Required

All operations target user-level paths — `~/.local/bin`, `~/scoop` (Windows), `/opt/homebrew` (macOS).
