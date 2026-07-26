# ==========================================================
# functions.ps1  —  ultra-profile function library
# Single source of truth for all profile functions.
# Dot-sourced by profile.ps1; do not run directly.
# ==========================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ── Internal helpers ──────────────────────────────────────────
function Test-IsWindows {
    $IsWindows -or ($env:OS -eq 'Windows_NT')
}

function Test-IsInteractive {
    if ($env:CI) { return $false }
    try { [Environment]::UserInteractive -and ($Host.Name -match 'ConsoleHost|Visual Studio Code Host') }
    catch { $false }
}

function Import-IfAvailable {
    param([Parameter(Mandatory)][string]$ModuleName)
    if (Get-Module -ListAvailable -Name $ModuleName) {
        Import-Module $ModuleName -ErrorAction SilentlyContinue | Out-Null
        return $true
    }
    $false
}

function _Get-VenvPython {
    param([Parameter(Mandatory)][string]$RepoRoot)
    $venvPy = if ($IsMacOS -or $IsLinux) {
        Join-Path $RepoRoot '.venv/bin/python3'
    } else {
        Join-Path $RepoRoot '.venv\Scripts\python.exe'
    }
    if (Test-Path -LiteralPath $venvPy) { return $venvPy }
    foreach ($cmd in @('python3', 'python')) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) { return $cmd }
    }
    throw 'Python not found. Install Python 3.9+ or run Invoke-ProjectSetup first.'
}

function Add-PathFront {
    param([Parameter(Mandatory)][string]$Dir)
    if (-not $Dir -or -not (Test-Path -LiteralPath $Dir)) { return }
    $sep   = [IO.Path]::PathSeparator
    $parts = $env:PATH -split [regex]::Escape($sep)
    if ($parts | Where-Object { $_ -and ($_ -ieq $Dir) }) { return }
    $env:PATH = $Dir + $sep + $env:PATH
}

$IsInteractive = Test-IsInteractive

# ── PATH bootstrap ────────────────────────────────────────────
$_ub = Join-Path $HOME '.local/bin'
if (-not (Test-Path -LiteralPath $_ub)) { try { New-Item -ItemType Directory -Path $_ub -Force | Out-Null } catch { } }
Add-PathFront -Dir $_ub
Remove-Variable _ub

if (Test-IsWindows) {
    Add-PathFront -Dir (Join-Path $HOME 'scoop\shims')
} else {
    Add-PathFront -Dir '/opt/homebrew/bin'
    Add-PathFront -Dir '/usr/local/bin'
}

# ── Navigation ────────────────────────────────────────────────
function ..   { Set-Location .. }
function ...  { Set-Location ../.. }
function .... { Set-Location ../../.. }


# ── Prompt ────────────────────────────────────────────────────
function Prompt {
    $ms   = if ((Get-History).Count -gt 0) {
        [math]::Round(((Get-History)[-1].EndExecutionTime - (Get-History)[-1].StartExecutionTime).TotalMilliseconds, 2)
    } else { 0 }
    $leaf = Split-Path -Leaf (Get-Location)
    if (-not $leaf) { $leaf = (Get-Location).Path }
    "/$leaf | ${ms}ms > "
}

# ── Windows: MSI extractor ────────────────────────────────────
function Expand-Msi {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][Alias('FullName','Path')][string]$MsiPath,
        [string]$Destination
    )
    if (-not (Test-IsWindows)) { throw 'Expand-Msi is Windows-only.' }
    $src = (Resolve-Path -Path $MsiPath -ErrorAction Stop).ProviderPath
    if (-not (Test-Path -LiteralPath $src -PathType Leaf)) { throw "Not a file: '$src'" }
    if ($Destination) {
        if (-not (Test-Path -LiteralPath $Destination)) { New-Item -ItemType Directory -Path $Destination -Force | Out-Null }
        $dest = (Resolve-Path -LiteralPath $Destination).ProviderPath
    } else {
        $dest = Join-Path (Split-Path $src -Parent) ([IO.Path]::GetFileNameWithoutExtension($src))
        if (-not (Test-Path -LiteralPath $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
    }
    $p = Start-Process msiexec.exe -ArgumentList "/a `"$src`" /qn TARGETDIR=`"$dest`"" -Wait -NoNewWindow -PassThru
    if ($p.ExitCode -ne 0) { throw "msiexec failed (exit $($p.ExitCode))." }
    $dest
}

# ── Windows: AWS WorkSpaces PCoIP clipboard ───────────────────
function Update-AWSClipboardRedirection {
    [CmdletBinding()]
    param([switch]$RestartNow)
    if (-not (Test-IsWindows)) { throw 'Update-AWSClipboardRedirection is Windows-only.' }

    $regPaths = @(
        'SOFTWARE\Policies\Teradici\PCoIP\pcoip_admin_defaults',
        'SOFTWARE\Policies\Teradici\PCoIP\pcoip_admin'
    )
    $base    = [Microsoft.Win32.RegistryKey]::OpenBaseKey(
        [Microsoft.Win32.RegistryHive]::LocalMachine, [Microsoft.Win32.RegistryView]::Registry64)
    $changed = $false

    foreach ($sub in $regPaths) {
        try {
            $key     = $base.CreateSubKey($sub, [Microsoft.Win32.RegistryKeyPermissionCheck]::ReadWriteSubTree)
            $current = $key.GetValue('pcoip.server_clipboard_state', $null,
                           [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
            $kind    = try { $key.GetValueKind('pcoip.server_clipboard_state') } catch { $null }
            if ($null -eq $current -or $kind -ne [Microsoft.Win32.RegistryValueKind]::DWord -or [int]$current -ne 1) {
                $key.SetValue('pcoip.server_clipboard_state', 1, [Microsoft.Win32.RegistryValueKind]::DWord)
                Write-Host ("Updated  HKLM:\{0}" -f $sub) -ForegroundColor Green
                $changed = $true
            } else {
                Write-Host ("OK       HKLM:\{0}" -f $sub) -ForegroundColor DarkGreen
            }
            $key.Close()
        } catch { Write-Warning ("Failed HKLM:\{0} - {1}" -f $sub, $_) }
    }
    $base.Close()

    if (-not $changed) { Write-Host 'No registry changes needed.' -ForegroundColor Yellow; return }
    if ($RestartNow) {
        Restart-Service -Name PCoIPAgent -Force -ErrorAction Stop
        Write-Host 'PCoIPAgent restarted.' -ForegroundColor Green
    } else {
        Write-Host 'Restart PCoIPAgent when convenient to apply changes.' -ForegroundColor Yellow
    }
}

# ── Windows: SecretStore ──────────────────────────────────────
function Unlock-DevSecretStore {
    [CmdletBinding()]
    param()
    if (-not (Test-IsWindows)) { Write-Host 'Windows-only.'; return }
    if (-not (Get-Module -ListAvailable -Name Microsoft.PowerShell.SecretManagement)) {
        Write-Host 'SecretManagement module not installed.'; return
    }
    Import-Module Microsoft.PowerShell.SecretManagement -ErrorAction SilentlyContinue | Out-Null
    $pw = Read-Host 'SecretStore password' -AsSecureString
    try   { Unlock-SecretStore -Password $pw -ErrorAction Stop; Write-Host 'SecretStore unlocked.' }
    finally { if ($pw) { $pw.Dispose() } }
}

function Set-Secrets {
    [CmdletBinding()]
    param()
    if (-not (Test-IsWindows)) { Write-Host 'Windows-only.'; return }
    try {
        Install-Module Microsoft.PowerShell.SecretManagement -Scope CurrentUser -Force -ErrorAction Stop
        Install-Module Microsoft.PowerShell.SecretStore       -Scope CurrentUser -Force -ErrorAction Stop
        Import-Module  Microsoft.PowerShell.SecretManagement  -ErrorAction SilentlyContinue | Out-Null

        $vaults = Get-SecretVault -ErrorAction SilentlyContinue
        if (-not ($vaults | Where-Object Name -eq 'SecretStore')) {
            Register-SecretVault -Name SecretStore -ModuleName Microsoft.PowerShell.SecretStore -DefaultVault -ErrorAction Stop
        } else {
            Set-SecretVaultDefault -Name SecretStore -ErrorAction SilentlyContinue
        }
        Set-SecretStoreConfiguration -Scope CurrentUser -Authentication Password -Interaction Prompt -ErrorAction Stop
        Set-Secret -Name OP_SERVICE_ACCOUNT_TOKEN -Secret (Read-Host 'OP service account token' -AsSecureString) -ErrorAction Stop
        Get-Secret -Name OP_SERVICE_ACCOUNT_TOKEN -ErrorAction Stop | Out-Null
        Write-Host 'OP token stored.' -ForegroundColor Green
    } catch { Write-Error ("Set-Secrets failed: {0}" -f $_) }
}

# ── 1Password CLI ─────────────────────────────────────────────
function Connect-OpSignin {
    [CmdletBinding()]
    param()
    if (-not (Get-Command op -ErrorAction SilentlyContinue)) {
        if ($IsInteractive) { Write-Host '1Password CLI not installed. Run Invoke-BrewToolset or Invoke-ScoopToolset.' -ForegroundColor Yellow }
        return $false
    }
    $null = op whoami 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Host '1Password CLI: Already signed in' -ForegroundColor Green; return $true }

    $tok = $null
    if (Test-IsWindows) {
        if (Import-IfAvailable 'Microsoft.PowerShell.SecretManagement') {
            $sec = Get-Secret -Name OP_SERVICE_ACCOUNT_TOKEN -ErrorAction SilentlyContinue
            if ($sec) {
                $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
                try   { $tok = [Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr) }
                finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
            }
        }
    } else {
        try {
            $tok = (& /usr/bin/security find-generic-password -s op_service_account_token    -w 2>$null)
            if (-not $tok) { $tok = (& /usr/bin/security find-generic-password -s OP_SERVICE_ACCOUNT_TOKEN -w 2>$null) }
            if ($tok) { $tok = $tok.Trim() }
        } catch { $tok = $null }
    }

    if (-not $tok) { Write-Warning '1Password CLI: OP_SERVICE_ACCOUNT_TOKEN missing.'; return $false }
    $env:OP_SERVICE_ACCOUNT_TOKEN = $tok
    $null = op whoami --account 'code-svc' 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Host '1Password CLI: Signed in as code-svc' -ForegroundColor Green; return $true }
    Write-Warning '1Password CLI: Sign-in failed. Verify OP_SERVICE_ACCOUNT_TOKEN.'
    return $false
}

# ── Package management ────────────────────────────────────────
function Get-DesiredScoopPackages {
    [CmdletBinding()]
    param()
    @(
        @{ Name = '1password-cli';  Bucket = 'extras'   }
        @{ Name = 'dotnet-sdk-9.0'; Bucket = 'versions' }
        @{ Name = 'gh';             Bucket = 'main'     }
        @{ Name = 'git';            Bucket = 'main'     }
        @{ Name = 'nodejs-lts';     Bucket = 'main'     }
        @{ Name = 'python';         Bucket = 'main'     }
        @{ Name = 'pwsh';           Bucket = 'main'     }
    )
}

function Get-DesiredBrewToolset {
    [CmdletBinding()]
    param()
    [PSCustomObject]@{
        Packages = @('1password-cli','dotnet','gh','git','node','python@3','powershell')
        Casks    = @('jupyterlab')
    }
}

function Invoke-ScoopToolset {
    [CmdletBinding()]
    param([switch]$DryRun)
    if (-not (Test-IsWindows))                                   { throw 'Windows-only.' }
    if (-not (Get-Command scoop -ErrorAction SilentlyContinue))  { throw 'scoop not found. Install from https://scoop.sh' }

    $existing = @()
    try {
        scoop bucket list 2>$null | ForEach-Object {
            $n = if ($_ -is [string]) { $_ } elseif ($_.PSObject.Properties['Name']) { $_.Name } else { $_.ToString() }
            $t = $n.TrimStart('*',' ').Trim(); if ($t) { $existing += $t }
        }
    } catch { }

    foreach ($b in @('versions','main','extras')) {
        if ($existing -contains $b) { continue }
        if ($DryRun) { Write-Host "DRY-RUN: scoop bucket add $b"; continue }
        Write-Host ">>> scoop bucket add $b"
        scoop bucket add $b | Out-Null
    }

    $installed = @{}
    try {
        scoop list 2>$null | ForEach-Object {
            if ($null -eq $_) { return }
            $n = if ($_.PSObject.Properties['Name'] -and $_.Name) { $_.Name }
                 else { ($_.ToString() -split '\s+')[0] }
            if ($n -and $n -notmatch '^(Installed|Name|---)') { $installed[$n.ToLower()] = $true }
        }
    } catch { }

    foreach ($pkg in Get-DesiredScoopPackages) {
        $q = if ($pkg.Bucket -and $pkg.Bucket -ne 'main') { "$($pkg.Bucket)/$($pkg.Name)" } else { $pkg.Name }
        if ($installed.ContainsKey($pkg.Name.ToLower())) {
            if ($DryRun) { Write-Host "DRY-RUN: scoop update $q"; continue }
            Write-Host ">>> scoop update $q"; scoop update $q | Out-Null
        } else {
            if ($DryRun) { Write-Host "DRY-RUN: scoop install $q"; continue }
            Write-Host ">>> scoop install $q"; scoop install $q | Out-Null
        }
    }
    Write-Host 'Scoop toolset complete.' -ForegroundColor Green
}

function Invoke-BrewToolset {
    [CmdletBinding()]
    param([switch]$DryRun)
    if (Test-IsWindows)                                          { throw 'macOS/Linux-only.' }
    if (-not (Get-Command brew -ErrorAction SilentlyContinue))   { throw 'brew not found. Install from https://brew.sh' }

    $desired  = Get-DesiredBrewToolset
    $formulae = @{}; (& brew list --formula 2>$null) | ForEach-Object { if ($_) { $formulae[$_.ToLower()] = $true } }
    $casks    = @{}; (& brew list --cask    2>$null) | ForEach-Object { if ($_) { $casks[$_.ToLower()]    = $true } }

    foreach ($pkg in $desired.Packages) {
        if ($formulae.ContainsKey($pkg.ToLower())) {
            if ($DryRun) { Write-Host "DRY-RUN: brew upgrade $pkg"; continue }
            Write-Host ">>> brew upgrade $pkg"; & brew upgrade $pkg 2>&1 | Out-Null
        } else {
            if ($DryRun) { Write-Host "DRY-RUN: brew install $pkg"; continue }
            Write-Host ">>> brew install $pkg"; & brew install $pkg 2>&1 | Out-Null
        }
    }
    foreach ($cask in $desired.Casks) {
        if ($casks.ContainsKey($cask.ToLower())) {
            if ($DryRun) { Write-Host "DRY-RUN: brew upgrade --cask $cask"; continue }
            Write-Host ">>> brew upgrade --cask $cask"; & brew upgrade --cask $cask 2>&1 | Out-Null
        } else {
            if ($DryRun) { Write-Host "DRY-RUN: brew install --cask $cask"; continue }
            Write-Host ">>> brew install --cask $cask"; & brew install --cask $cask 2>&1 | Out-Null
        }
    }
    Write-Host 'Homebrew toolset complete.' -ForegroundColor Green
}

# ── GitHub / Repo ─────────────────────────────────────────────
function New-GitHubRepo {
    [CmdletBinding()]
    param()
    if (-not (Get-Command gh  -ErrorAction SilentlyContinue)) { Write-Error 'gh not found. Run Invoke-BrewToolset / Invoke-ScoopToolset.'; return }
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Write-Error 'git not found.'; return }

    $ghOk = $false
    try { gh auth status --hostname github.com 2>$null | Out-Null; $ghOk = ($LASTEXITCODE -eq 0) } catch { }

    if (-not $ghOk) {
        $tok = $null
        if (-not (Test-IsWindows)) {
            try { $tok = (& /usr/bin/security find-generic-password -s github_pat -w 2>$null)?.Trim() } catch { }
        } elseif (Import-IfAvailable 'Microsoft.PowerShell.SecretManagement') {
            foreach ($n in @('GH_PAT','GitHub-PAT')) {
                $sec = Get-Secret -Name $n -ErrorAction SilentlyContinue
                if ($sec) {
                    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
                    try   { $tok = [Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr) }
                    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
                    if ($tok) { break }
                }
            }
        }
        if ($tok) {
            $tok | gh auth login --hostname github.com --git-protocol https --with-token 2>$null | Out-Null
            $ghOk = ($LASTEXITCODE -eq 0)
        }
    }

    if (-not $ghOk) { Write-Error 'gh auth required. Run gh auth login or Set-Secrets.'; return }

    $name = Split-Path -Leaf (Get-Location)
    Write-Host "Creating private GitHub repo: $name" -ForegroundColor Cyan

    if (-not (Test-Path '.git'))       { git init; if ($LASTEXITCODE -ne 0) { Write-Error 'git init failed'; return } }
    if (-not (Test-Path '.gitignore')) { ".env`n.env.*`n!.env.example`nnode_modules/`n.DS_Store" | Out-File '.gitignore' -Encoding utf8 -NoNewline }
    if (-not (Test-Path 'README.md'))  { "# $name`n`nTODO: Add project description`n" | Out-File 'README.md' -Encoding utf8 -NoNewline }

    git add .; git commit -m 'Initial commit'
    gh repo create $name --private --source=. --push
    if ($LASTEXITCODE -ne 0) { Write-Error 'gh repo create failed'; return }
    Write-Host "Created: https://github.com/$(gh api user --jq .login)/$name" -ForegroundColor Green
}

function Invoke-AdoRepoSync {
    <#
    .SYNOPSIS
        Generate or apply Azure DevOps work item updates from the current repo.
    .DESCRIPTION
        Thin wrapper around ia-ado-pbi-automation/ado_repo_sync.py. Run this
        from any source repo to inspect git/docs evidence and map completed work
        to an existing ADO parent work item and its descendants.

        Default behavior is dry-run/preview only. Add -Apply to execute updates.
    .PARAMETER ParentId
        ADO parent/root work item ID whose descendants may be updated.
    .PARAMETER Repo
        Source git repo path. Defaults to current directory.
    .PARAMETER BaseRef
        Optional git ref to diff against, e.g. origin/main or HEAD~5.
    .PARAMETER Apply
        Apply the generated ADO update plan. Without this switch, previews only.
    .PARAMETER AutomationRepo
        Path to ia-ado-pbi-automation. Defaults to ADO_PBI_AUTOMATION_REPO env var
        or common ~/foundry / OneDrive locations.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][int]$ParentId,
        [string]$Repo = (Get-Location).Path,
        [string]$BaseRef,
        [switch]$Apply,
        [string]$AutomationRepo
    )

    if (-not (Get-Command python3 -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw 'Python not found. Install Python or run Invoke-BrewToolset / Invoke-ScoopToolset.'
    }
    $python = if (Get-Command python3 -ErrorAction SilentlyContinue) { 'python3' } else { 'python' }

    $candidates = @()
    if ($AutomationRepo) { $candidates += $AutomationRepo }
    if ($env:ADO_PBI_AUTOMATION_REPO) { $candidates += $env:ADO_PBI_AUTOMATION_REPO }
    # Local project copy takes precedence over the central automation repo
    $candidates += Join-Path $Repo '_engineer/ado-sync'
    $candidates += @(
        (Join-Path $HOME 'foundry/ia-ado-pbi-automation'),
        (Join-Path $HOME 'OneDrive - Wellpath/foundry/ia-ado-pbi-automation'),
        (Join-Path $HOME 'Library/CloudStorage/OneDrive-Wellpath/foundry/ia-ado-pbi-automation')
    )

    $root = $null
    foreach ($candidate in $candidates) {
        if (-not $candidate) { continue }
        $script = Join-Path $candidate 'ado_repo_sync.py'
        if (Test-Path -LiteralPath $script) {
            $root = (Resolve-Path -LiteralPath $candidate).ProviderPath
            break
        }
    }
    if (-not $root) {
        throw "Could not find ia-ado-pbi-automation/ado_repo_sync.py. Set `$env:ADO_PBI_AUTOMATION_REPO or pass -AutomationRepo."
    }

    $syncScript = Join-Path $root 'ado_repo_sync.py'
    $repoPath = (Resolve-Path -LiteralPath $Repo -ErrorAction Stop).ProviderPath
    if (-not (Test-Path -LiteralPath (Join-Path $repoPath '.git'))) {
        throw "Not a git repository: $repoPath"
    }

    $args = @($syncScript, '--repo', $repoPath, '--parent-id', $ParentId.ToString())
    if ($BaseRef) { $args += @('--base-ref', $BaseRef) }
    if ($Apply) { $args += '--apply' }

    Write-Host ">>> $python $($args -join ' ')" -ForegroundColor Yellow
    & $python @args
}

function Invoke-AdoCreator {
    <#
    .SYNOPSIS
        Run the interactive AI ADO work item creator for the current project.
    .DESCRIPTION
        Thin wrapper around _engineer/ado-sync/ai_ado_creator.py.
        Uses the project's .venv Python when available.
    .PARAMETER Repo
        Path to the project repo. Defaults to current directory.
    #>
    [CmdletBinding()]
    param(
        [string]$Repo = (Get-Location).Path
    )

    $repoPath = (Resolve-Path -LiteralPath $Repo -ErrorAction Stop).ProviderPath
    if (-not (Test-Path -LiteralPath (Join-Path $repoPath '.git'))) {
        throw "Not a git repository: $repoPath"
    }

    $script = Join-Path $repoPath '_engineer/ado-sync/ai_ado_creator.py'
    if (-not (Test-Path -LiteralPath $script)) {
        throw "ai_ado_creator.py not found at: $script"
    }

    $python = _Get-VenvPython -RepoRoot $repoPath
    Write-Host ">>> $python $script" -ForegroundColor Yellow
    Push-Location $repoPath
    try { & $python $script }
    finally { Pop-Location }
}

function Invoke-HipaaRedact {
    <#
    .SYNOPSIS
        De-identify a discharge summary PDF using HIPAA Safe Harbor rules.
    .DESCRIPTION
        Thin wrapper around _engineer/hipaa-sanitize/hipaa_redact.py.
        Uses the project's .venv Python when available.
    .PARAMETER InputPdf
        Path to the source PDF to de-identify.
    .PARAMETER OutputPdf
        Output path (default: <input>_REDACTED.pdf alongside the source).
    .PARAMETER OffsetDays
        Days to shift all dates (default: random 30-180).
    .PARAMETER Names
        Known patient/provider names to explicitly redact.
    .PARAMETER Facilities
        Known facility names to explicitly redact.
    .PARAMETER Repo
        Path to the project repo containing hipaa_redact.py. Defaults to current directory.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$InputPdf,
        [string]$OutputPdf,
        [int]$OffsetDays,
        [string[]]$Names      = @(),
        [string[]]$Facilities = @(),
        [string]$Repo         = (Get-Location).Path
    )

    $repoPath = (Resolve-Path -LiteralPath $Repo -ErrorAction Stop).ProviderPath
    $script   = Join-Path $repoPath '_engineer/hipaa-sanitize/hipaa_redact.py'
    if (-not (Test-Path -LiteralPath $script)) {
        throw "hipaa_redact.py not found at: $script"
    }

    $inputPath = (Resolve-Path -LiteralPath $InputPdf -ErrorAction Stop).ProviderPath
    $python    = _Get-VenvPython -RepoRoot $repoPath

    $args = @($script, $inputPath)
    if ($OutputPdf)    { $args += $OutputPdf }
    if ($OffsetDays)   { $args += @('--offset-days', $OffsetDays.ToString()) }
    if ($Names.Count)  { $args += @('--names')      + $Names }
    if ($Facilities.Count) { $args += @('--facilities') + $Facilities }

    Write-Host ">>> $python $($args -join ' ')" -ForegroundColor Yellow
    & $python @args
}

function Invoke-ProjectSetup {
    <#
    .SYNOPSIS
        Create the Python virtual environment and install project dependencies.
    .DESCRIPTION
        Calls _engineer/dev-env/init-repo-tooling.ps1 from the project root.
        Equivalent to: pwsh -NoProfile -File _engineer/dev-env/init-repo-tooling.ps1
    .PARAMETER Repo
        Path to the project root. Defaults to current directory.
    #>
    [CmdletBinding()]
    param(
        [string]$Repo = (Get-Location).Path
    )

    $repoPath = (Resolve-Path -LiteralPath $Repo -ErrorAction Stop).ProviderPath
    $setupScript = Join-Path $repoPath '_engineer/dev-env/init-repo-tooling.ps1'
    if (-not (Test-Path -LiteralPath $setupScript)) {
        throw "init-repo-tooling.ps1 not found at: $setupScript"
    }

    Push-Location $repoPath
    try { & $setupScript }
    finally { Pop-Location }
}

function New-RepoFromTemplate {
    <#
    .SYNOPSIS
        Clone <your-org>/repo-template as a new repo, or apply its files to an existing one.
    .PARAMETER Name         New repo folder name (new-repo mode)
    .PARAMETER Destination  Parent directory (new-repo mode, defaults to cwd)
    .PARAMETER FreshHistory Squash template history to a single Initial commit
    .PARAMETER Apply        Path to existing repo (apply mode — copies missing files in)
    .PARAMETER Force        Overwrite existing files (apply mode)
    #>
    [CmdletBinding(DefaultParameterSetName = 'New')]
    param(
        [Parameter(ParameterSetName = 'New',   Mandatory)][string]$Name,
        [Parameter(ParameterSetName = 'New')]              [string]$Destination = (Get-Location).Path,
        [Parameter(ParameterSetName = 'New')]              [switch]$FreshHistory,
        [Parameter(ParameterSetName = 'Apply', Mandatory)][string]$Apply,
        [Parameter(ParameterSetName = 'Apply')]            [switch]$Force
    )

    $url = 'https://github.com/<your-org>/repo-template'
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Write-Error 'git not found.'; return }

    if ($PSCmdlet.ParameterSetName -eq 'Apply') {
        $target = try { (Resolve-Path -LiteralPath $Apply -ErrorAction Stop).ProviderPath }
                  catch { Write-Error "Not found: '$Apply'"; return }
        if (-not (Test-Path (Join-Path $target '.git'))) { Write-Warning "'$target' has no .git folder." }

        $tmp = Join-Path ([IO.Path]::GetTempPath()) ([IO.Path]::GetRandomFileName())
        Write-Host ">>> git clone --depth 1 $url (temp)" -ForegroundColor Yellow
        git clone --depth 1 --quiet $url $tmp
        if ($LASTEXITCODE -ne 0) { Write-Error 'Clone failed.'; return }

        try {
            $gitDir  = Join-Path $tmp '.git'
            $copied  = [Collections.Generic.List[string]]::new()
            $skipped = [Collections.Generic.List[string]]::new()
            $over    = [Collections.Generic.List[string]]::new()

            Get-ChildItem -LiteralPath $tmp -Recurse -File |
                Where-Object { $_.FullName -notlike "$gitDir*" } |
                ForEach-Object {
                    $rel  = $_.FullName.Substring($tmp.Length).TrimStart([IO.Path]::DirectorySeparatorChar)
                    $dest = Join-Path $target $rel
                    $dir  = Split-Path $dest -Parent
                    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
                    if (Test-Path $dest) {
                        if ($Force) { Copy-Item -LiteralPath $_.FullName -Destination $dest -Force; $over.Add($rel) }
                        else        { $skipped.Add($rel) }
                    } else { Copy-Item -LiteralPath $_.FullName -Destination $dest; $copied.Add($rel) }
                }

            Write-Host ''
            if ($copied.Count)  { Write-Host "Copied ($($copied.Count)):"        -ForegroundColor Green;   $copied  | ForEach-Object { Write-Host "  + $_" -ForegroundColor Green } }
            if ($over.Count)    { Write-Host "Overwritten ($($over.Count)):"     -ForegroundColor Yellow;  $over    | ForEach-Object { Write-Host "  ~ $_" -ForegroundColor Yellow } }
            if ($skipped.Count) { Write-Host "Skipped ($($skipped.Count)) [-Force to overwrite]:" -ForegroundColor DarkGray; $skipped | ForEach-Object { Write-Host "  = $_" -ForegroundColor DarkGray } }
            Write-Host ''
            Write-Host "Template applied to: $target" -ForegroundColor Green
        } finally { Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue }

        Write-Host ''
        $ans = Read-Host 'Initialize AI context files? (CLAUDE.md, copilot-instructions.md) [Y/n]'
        if ($ans -eq '' -or $ans -match '^[Yy]') {
            Initialize-AiContext -Path $target
        }
        return
    }

    $resolvedDest = try { (Resolve-Path -LiteralPath $Destination -ErrorAction Stop).ProviderPath }
                    catch {
                        Write-Host "Creating '$Destination'..." -ForegroundColor Yellow
                        New-Item -ItemType Directory -Path $Destination -Force | Out-Null
                        (Resolve-Path -LiteralPath $Destination).ProviderPath
                    }
    $target = Join-Path $resolvedDest $Name
    if (Test-Path $target) { Write-Error "Already exists: '$target'. Use -Apply to merge files into it."; return }

    Write-Host ">>> git clone $url `"$target`"" -ForegroundColor Yellow
    git clone $url $target
    if ($LASTEXITCODE -ne 0) { Write-Error 'Clone failed.'; return }

    Push-Location $target
    try {
        if ($FreshHistory) {
            Write-Host '>>> Squashing to single Initial commit...' -ForegroundColor Yellow
            git checkout --orphan _init; git add -A; git commit -m 'Initial commit'
            $branch = (git symbolic-ref refs/remotes/origin/HEAD --short 2>$null) -replace '^origin/',''
            if (-not $branch) { $branch = 'main' }
            git branch -D $branch 2>$null | Out-Null; git branch -m $branch
        }
        git remote remove origin
        Write-Host ''
        Write-Host "Ready at: $target" -ForegroundColor Green
        if ($FreshHistory) { Write-Host 'History squashed to single Initial commit.' -ForegroundColor Green }
        Write-Host 'Run New-GitHubRepo inside the folder to push to GitHub.' -ForegroundColor Cyan
    } catch { Write-Error "Failed: $_" }
    finally  { Pop-Location }
}

# ── AI context scaffolding ────────────────────────────────────
function Initialize-AiContext {
    <#
    .SYNOPSIS
        Scaffolds AI context files into a repository.
    .DESCRIPTION
        Creates starter files for Claude Code (CLAUDE.md) and GitHub Copilot
        (.github/copilot-instructions.md).
        Skips any file that already exists unless -Force is specified.
    .PARAMETER Path
        Target repository root. Defaults to the current directory.
    .PARAMETER Force
        Overwrite files that already exist.
    #>
    [CmdletBinding()]
    param(
        [string]$Path  = (Get-Location).Path,
        [switch]$Force
    )

    $root = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).ProviderPath
    $name = Split-Path $root -Leaf

    $files = [ordered]@{
        'CLAUDE.md' = @"
# $name

## Overview
TODO: Describe what this project does and why it exists.

## Architecture
TODO: Describe the high-level structure — key directories, layers, data flow.

## Common Commands
\`\`\`bash
# TODO: add build, test, lint, run commands
\`\`\`

## Key Files
| File / Directory | Purpose |
|-----------------|---------|
| TODO            |         |

## Conventions
TODO: Note any naming conventions, coding standards, or patterns the AI should follow.

## Out of Scope
TODO: List anything the AI should not touch or suggest changes to.
"@

        '.github/copilot-instructions.md' = @"
# GitHub Copilot Instructions — $name

## Project Context
TODO: Describe the project so Copilot understands the domain.

## Preferred Patterns
- TODO: List preferred libraries, frameworks, or approaches.

## Avoid
- TODO: List patterns, libraries, or anti-patterns to avoid.

## Testing
- TODO: Describe the testing approach (unit, integration, e2e).
"@

    }

    $created  = [Collections.Generic.List[string]]::new()
    $skipped  = [Collections.Generic.List[string]]::new()

    foreach ($rel in $files.Keys) {
        $dest   = Join-Path $root $rel
        $dir    = Split-Path $dest -Parent
        $exists = Test-Path -LiteralPath $dest

        if ($exists -and -not $Force) {
            $skipped.Add($rel)
            continue
        }

        if (-not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
        $files[$rel] | Out-File -FilePath $dest -Encoding utf8 -NoNewline -Force
        $created.Add($rel)
    }

    Write-Host ''
    if ($created.Count) {
        Write-Host "AI context files created:" -ForegroundColor Green
        $created | ForEach-Object { Write-Host "  + $_" -ForegroundColor Green }
    }
    if ($skipped.Count) {
        Write-Host "Skipped (already exist) [-Force to overwrite]:" -ForegroundColor DarkGray
        $skipped | ForEach-Object { Write-Host "  = $_" -ForegroundColor DarkGray }
    }
    Write-Host ''
    Write-Host 'Fill in the TODOs - the more context you provide, the better the AI assistance.' -ForegroundColor Cyan
}

# ── Auth status ───────────────────────────────────────────────
function Show-AuthStatus {
    [CmdletBinding()]
    param()

    function _check {
        param([string]$Tool, [scriptblock]$Block)
        if (-not (Get-Command $Tool -ErrorAction SilentlyContinue)) {
            Write-Host (' [-] {0,-4}' -f $Tool) -ForegroundColor DarkGray -NoNewline
            Write-Host '  not installed' -ForegroundColor DarkGray
            return
        }
        try {
            $detail = & $Block
            Write-Host (' [') -ForegroundColor DarkGray -NoNewline
            Write-Host ('✓') -ForegroundColor Green -NoNewline
            Write-Host ('] {0,-4}' -f $Tool) -ForegroundColor DarkGray -NoNewline
            Write-Host "  $detail" -ForegroundColor Green
        } catch {
            Write-Host (' [') -ForegroundColor DarkGray -NoNewline
            Write-Host ('✗') -ForegroundColor Red -NoNewline
            Write-Host ('] {0,-4}' -f $Tool) -ForegroundColor DarkGray -NoNewline
            Write-Host '  not signed in' -ForegroundColor Red
        }
    }

    Write-Host ''
    Write-Host ' auth status' -ForegroundColor Cyan -NoNewline
    Write-Host '  ·  gh  az  op' -ForegroundColor DarkGray
    Write-Host (' ' + '─' * 44) -ForegroundColor DarkGray

    _check 'gh' {
        $out = gh auth status 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) { throw }
        $account = if ($out -match 'Logged in to .+ account (.+?) \(') { $Matches[1] }
                   else { ($out -split "`n" | Where-Object { $_ -match '\S' } | Select-Object -First 1).Trim() }
        $host_   = if ($out -match 'Logged in to (\S+)') { $Matches[1] } else { 'github.com' }
        "$account @ $host_"
    }

    _check 'az' {
        $json = az account show 2>$null | ConvertFrom-Json -ErrorAction Stop
        if (-not $json) { throw }
        "$($json.name) ($($json.id.Substring(0,8))...)"
    }

    _check 'op' {
        $out = op whoami 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) { throw }
        ($out -split "`n" | Where-Object { $_ -match '\S' } | Select-Object -First 1).Trim()
    }

    Write-Host ''
}

# ── Function manifest & help ──────────────────────────────────
$script:_Manifest = @(
    [PSCustomObject]@{ P = 'ANY'; Name = '.. / ... / ....';                Note = 'Navigate up 1–3 levels' }
    [PSCustomObject]@{ P = 'WIN'; Name = 'Expand-Msi';                     Note = '-MsiPath <p> [-Destination <d>]' }
    [PSCustomObject]@{ P = 'WIN'; Name = 'Update-AWSClipboardRedirection'; Note = 'Fix PCoIP clipboard  [-RestartNow]' }
    [PSCustomObject]@{ P = 'WIN'; Name = 'Unlock-DevSecretStore';          Note = 'Unlock SecretManagement vault (interactive)' }
    [PSCustomObject]@{ P = 'WIN'; Name = 'Set-Secrets';                    Note = 'Store OP token in Windows SecretManagement' }
    [PSCustomObject]@{ P = 'WIN'; Name = 'Invoke-ScoopToolset';            Note = '[-DryRun]  install/update Scoop dev toolset' }
    [PSCustomObject]@{ P = 'MAC'; Name = 'Invoke-BrewToolset';             Note = '[-DryRun]  install/update Homebrew dev toolset' }
    [PSCustomObject]@{ P = 'ANY'; Name = 'Connect-OpSignin';               Note = 'Sign in to 1Password CLI via stored token' }
    [PSCustomObject]@{ P = 'ANY'; Name = 'New-GitHubRepo';                 Note = 'Init cwd and push to a new private GitHub repo' }
    [PSCustomObject]@{ P = 'ANY'; Name = 'Invoke-AdoRepoSync';              Note = '-ParentId <id> [-BaseRef <ref>] [-Apply]  sync repo work to ADO' }
    [PSCustomObject]@{ P = 'ANY'; Name = 'Invoke-AdoCreator';              Note = '[-Repo <path>]  run interactive AI ADO work item creator' }
    [PSCustomObject]@{ P = 'ANY'; Name = 'Invoke-HipaaRedact';             Note = '-InputPdf <p> [-OutputPdf <p>] [-OffsetDays <n>] [-Names ...] [-Facilities ...]' }
    [PSCustomObject]@{ P = 'ANY'; Name = 'Invoke-ProjectSetup';            Note = '[-Repo <path>]  create .venv and install requirements.txt' }
    [PSCustomObject]@{ P = 'ANY'; Name = 'New-RepoFromTemplate';           Note = '-Name <n> [-Destination <p>] [-FreshHistory] | -Apply <path> [-Force]' }
    [PSCustomObject]@{ P = 'ANY'; Name = 'Initialize-AiContext';           Note = 'Scaffold CLAUDE.md, copilot-instructions.md  [-Path] [-Force]' }
    [PSCustomObject]@{ P = 'ANY'; Name = 'Show-AuthStatus';                Note = 'Show gh / az / op login status' }
    [PSCustomObject]@{ P = 'ANY'; Name = 'Show-ProfileHelp';               Note = 'Show this list again' }
)

function Show-ProfileHelp {
    [CmdletBinding()]
    param()
    $w = ($script:_Manifest | ForEach-Object { $_.Name.Length } | Measure-Object -Maximum).Maximum + 2
    Write-Host ''
    Write-Host ' ultra-profile' -ForegroundColor Cyan -NoNewline
    Write-Host '  ·  available functions' -ForegroundColor DarkGray
    Write-Host (' ' + ('─' * ($w + 34))) -ForegroundColor DarkGray
    foreach ($e in $script:_Manifest) {
        $pColor = switch ($e.P.Trim()) { 'WIN' { 'Blue' } 'MAC' { 'Green' } default { 'DarkGray' } }
        Write-Host (' [{0}] ' -f $e.P) -ForegroundColor $pColor -NoNewline
        Write-Host $e.Name.PadRight($w)  -ForegroundColor White  -NoNewline
        Write-Host $e.Note -ForegroundColor DarkGray
    }
    Write-Host ''
}

function Launch-Code {
    # ==========================================================
# launch-code.ps1
# Portable VS Code launcher — macOS and Windows.
# Wires Homebrew (macOS) or Scoop (Windows) paths, resolves dotnet,
# exposes DEV_FUNCTIONS for VS Code terminal profiles, and opens a workspace.
#
# LAUNCH:
#   pwsh -NoProfile ./launch-code.ps1 /path/to/workspace.code-workspace
#   pwsh -NoProfile ./launch-code.ps1 /path/to/workspace.code-workspace -PortableUserData
#   pwsh -NoProfile ./launch-code.ps1 /path/to/workspace.code-workspace -DevRoot ~/projects
# ==========================================================

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$WorkspaceFile,

    [switch]$PortableUserData,

    [string]$DevRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot

# --- Dev script wiring (used by VS Code terminal profiles) ---
$env:DEV_FUNCTIONS = Join-Path $repoRoot 'functions.ps1'

if ($DevRoot) {
    $env:DEV_ROOT = $DevRoot
}

# --- Validate workspace ---
if (-not (Test-Path -LiteralPath $WorkspaceFile)) {
    throw "WorkspaceFile not found: $WorkspaceFile"
}

# ── macOS ─────────────────────────────────────────────────────────────────────
if ($IsMacOS) {

    # Ensure Homebrew is on PATH (Finder-launched VS Code often misses it)
    foreach ($p in @('/opt/homebrew/bin', '/usr/local/bin')) {
        if ((Test-Path -LiteralPath $p) -and ($env:PATH -notmatch [regex]::Escape($p))) {
            $env:PATH = "${p}:$($env:PATH)"
        }
    }

    # Dotnet (brew-managed)
    $dotnetCmd = Get-Command dotnet -ErrorAction SilentlyContinue
    if ($dotnetCmd) {
        $dotnetRoot = Split-Path -Parent $dotnetCmd.Source
        $env:DOTNET_ROOT = $dotnetRoot
        if ($env:PATH -notmatch [regex]::Escape($dotnetRoot)) {
            $env:PATH = "${dotnetRoot}:$($env:PATH)"
        }
    }

    # VS Code binary
    $codeCmd = Get-Command code -ErrorAction SilentlyContinue
    if ($codeCmd) {
        $vscodeExe = $codeCmd.Source
    } else {
        $fallback = '/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code'
        if (-not (Test-Path -LiteralPath $fallback)) {
            throw "Could not find 'code' on PATH or VS Code at: $fallback"
        }
        $vscodeExe = $fallback
    }

    # Portable user-data dir
    $portableDir = Join-Path $HOME '.vscode-portable-user-data'
    $portableExtDir = Join-Path $portableDir 'extensions'

# ── Windows ───────────────────────────────────────────────────────────────────
} elseif ($IsWindows) {

    $scoopRoot  = Join-Path $env:USERPROFILE 'scoop'
    $scoopShims = Join-Path $scoopRoot 'shims'
    if (Test-Path -LiteralPath $scoopShims) {
        $env:PATH = "$scoopShims;$env:PATH"
    }

    # Dotnet — prefer pinned Scoop version, fallback to Get-Command
    $dotnetExe = @(
        (Join-Path $scoopRoot 'apps\dotnet-sdk-9.0\current\dotnet.exe'),
        (Join-Path $scoopRoot 'apps\dotnet-sdk\current\dotnet.exe')
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

    if (-not $dotnetExe) {
        $cmd = Get-Command dotnet -ErrorAction SilentlyContinue
        if ($cmd) { $dotnetExe = $cmd.Source }
    }
    if ($dotnetExe) {
        $dotnetRoot = Split-Path -Parent $dotnetExe
        $env:DOTNET_ROOT = $dotnetRoot
        $env:PATH = "$dotnetRoot;$env:PATH"
    }

    # VS Code binary (Scoop-managed)
    $vscodeExe = @(
        (Join-Path $scoopRoot 'apps\vscode\current\Code.exe'),
        (Join-Path $scoopRoot 'apps\vscode\current\bin\code.cmd')
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

    if (-not $vscodeExe) {
        throw "VS Code not found via Scoop. Expected at: $scoopRoot\apps\vscode\current\"
    }

    # Portable user-data dir (Scoop keeps it inside the app folder)
    $portableDir    = Join-Path $scoopRoot 'apps\vscode\current\data'
    $portableExtDir = $null  # Scoop manages extensions location internally

} else {
    throw 'launch-code.ps1 supports macOS and Windows only.'
}

# ── Launch ────────────────────────────────────────────────────────────────────
$codeArgs = @()

if ($PortableUserData) {
    if (-not (Test-Path -LiteralPath $portableDir)) {
        New-Item -ItemType Directory -Path $portableDir -Force | Out-Null
    }
    $codeArgs += '--user-data-dir'
    $codeArgs += $portableDir

    if ($portableExtDir) {
        $codeArgs += '--extensions-dir'
        $codeArgs += $portableExtDir
    }
}

$codeArgs += $WorkspaceFile

Start-Process -FilePath $vscodeExe -ArgumentList $codeArgs

}
