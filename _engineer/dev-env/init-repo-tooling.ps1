#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Initialize project tooling for this template repo (macOS and Windows).

.DESCRIPTION
  Checks for and installs: gitleaks, Python venv, pip deps, Node/npm deps, pre-commit hooks.
  Runs a gitleaks secret scan and outputs a pass/warn/fail summary.
  Works on macOS (brew) and Windows (winget/choco) via PowerShell Core.

.USAGE
  pwsh -NoProfile -File "_engineer/dev-env/init-repo-tooling.ps1"
#>

$ErrorActionPreference = 'Continue'
$pass = [System.Collections.Generic.List[string]]::new()
$warn = [System.Collections.Generic.List[string]]::new()
$fail = [System.Collections.Generic.List[string]]::new()

function Test-Cmd($name) { $null -ne (Get-Command $name -ErrorAction SilentlyContinue) }

function Write-Step($n, $label) {
    Write-Host "`n[$n] $label" -ForegroundColor Cyan
}

function Write-Ok($msg)   { Write-Host "  OK    $msg" -ForegroundColor Green  }
function Write-Warn($msg) { Write-Host "  WARN  $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  FAIL  $msg" -ForegroundColor Red    }

# Resolve repo root (script lives 2 levels deep: _engineer/dev-env/)
$repoRoot = $PSScriptRoot
1..2 | ForEach-Object { $repoRoot = Split-Path $repoRoot -Parent }
Set-Location $repoRoot

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " Project Init — $(Split-Path $repoRoot -Leaf)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ── 1. gitleaks ──────────────────────────────────────────────────────────────
Write-Step 1 "gitleaks (secret scanning)"

if (Test-Cmd "gitleaks") {
    $ver = gitleaks version 2>&1
    Write-Ok "gitleaks already installed ($ver)"
    $pass.Add("gitleaks installed")
} else {
    Write-Host "  Installing gitleaks..."
    $installed = $false
    if ($IsMacOS) {
        if (Test-Cmd "brew") {
            brew install gitleaks
            $installed = Test-Cmd "gitleaks"
        } else {
            Write-Warn "Homebrew not found. Install manually: https://github.com/gitleaks/gitleaks/releases"
        }
    } elseif ($IsWindows) {
        if (Test-Cmd "winget") {
            winget install gitleaks.gitleaks --silent --accept-package-agreements --accept-source-agreements
            $installed = Test-Cmd "gitleaks"
        } elseif (Test-Cmd "choco") {
            choco install gitleaks -y
            $installed = Test-Cmd "gitleaks"
        } else {
            Write-Warn "Neither winget nor choco found. Install manually: https://github.com/gitleaks/gitleaks/releases"
        }
    } else {
        Write-Warn "Linux: install gitleaks manually — https://github.com/gitleaks/gitleaks/releases"
    }

    if ($installed) {
        Write-Ok "gitleaks installed"
        $pass.Add("gitleaks installed")
    } else {
        Write-Err "gitleaks install failed or skipped"
        $fail.Add("gitleaks not installed — secret scanning unavailable")
    }
}

# ── 2. Python venv ───────────────────────────────────────────────────────────
Write-Step 2 "Python virtual environment"

$python = if ($IsMacOS -or $IsLinux) { "python3" } else { "python" }
$venvPip = if ($IsMacOS -or $IsLinux) { ".venv/bin/pip" } else { ".venv\Scripts\pip.exe" }

if (-not (Test-Cmd $python)) {
    Write-Err "Python not found — install Python 3.9+"
    $fail.Add("Python not installed")
} else {
    $pyVer = & $python --version 2>&1
    Write-Host "  Using $pyVer"

    if (-not (Test-Path ".venv")) {
        Write-Host "  Creating .venv..."
        & $python -m venv .venv
    }

    if (Test-Path ".venv") {
        Write-Ok ".venv exists"
        $pass.Add("Python venv ready")

        # Upgrade pip silently
        & $venvPip install --upgrade pip --quiet 2>$null

        # Install deps if requirements.txt exists
        if (Test-Path "requirements.txt") {
            Write-Host "  Installing pip dependencies..."
            $pipOut = & $venvPip install -r requirements.txt --quiet 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "pip dependencies installed"
                $pass.Add("pip deps installed")
            } else {
                Write-Err "pip install failed"
                Write-Host $pipOut
                $fail.Add("pip deps install failed")
            }
        } else {
            Write-Warn "No requirements.txt found — add dependencies when ready"
            $warn.Add("requirements.txt missing")
        }
    } else {
        Write-Err ".venv creation failed"
        $fail.Add("Python venv creation failed")
    }
}

# ── 3. Node.js ───────────────────────────────────────────────────────────────
Write-Step 3 "Node.js / npm"

if (Test-Cmd "node") {
    $nodeVer = node --version
    $npmVer  = npm --version
    Write-Ok "Node $nodeVer, npm $npmVer"
    $pass.Add("Node.js $nodeVer")

    foreach ($dir in @("backend", "frontend")) {
        if (Test-Path "$dir/package.json") {
            Write-Host "  Installing $dir npm deps..."
            Push-Location $dir
            npm install --silent
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "$dir npm deps installed"
                $pass.Add("$dir npm deps installed")
            } else {
                Write-Err "$dir npm install failed"
                $fail.Add("$dir npm install failed")
            }
            Pop-Location
        }
    }

    # Check if backend/frontend exist but are empty (template state)
    $emptyDirs = @("backend", "frontend") | Where-Object {
        (Test-Path $_) -and (-not (Test-Path "$_/package.json"))
    }
    if ($emptyDirs.Count -gt 0) {
        Write-Warn "$($emptyDirs -join ', ') director(ies) exist but have no package.json yet"
        $warn.Add("$($emptyDirs -join ', ') not initialized")
    }
} else {
    Write-Warn "Node.js not installed — required when backend/frontend are populated"
    $warn.Add("Node.js not installed")
}

# ── 4. pre-commit hooks ──────────────────────────────────────────────────────
Write-Step 4 "pre-commit hooks"

if (Test-Path ".pre-commit-config.yaml") {
    $precommitInstalled = $false

    if (Test-Cmd "pre-commit") {
        $precommitInstalled = $true
    } else {
        Write-Host "  Installing pre-commit..."
        # Try venv pip first, then system pip, then brew
        $pipCmds = @($venvPip, "pip3", "pip")
        foreach ($pip in $pipCmds) {
            if (Test-Path $pip -ErrorAction SilentlyContinue) {
                & $pip install pre-commit --quiet 2>$null
                if (Test-Cmd "pre-commit") { $precommitInstalled = $true; break }
            } elseif (Test-Cmd $pip) {
                & $pip install pre-commit --quiet 2>$null
                if (Test-Cmd "pre-commit") { $precommitInstalled = $true; break }
            }
        }
        if (-not $precommitInstalled -and $IsMacOS -and (Test-Cmd "brew")) {
            brew install pre-commit --quiet
            $precommitInstalled = Test-Cmd "pre-commit"
        }
    }

    if ($precommitInstalled) {
        Write-Ok "pre-commit installed ($(pre-commit --version))"
        $pass.Add("pre-commit installed")

        if (Test-Path ".git") {
            Write-Host "  Installing git hooks..."
            pre-commit install --install-hooks 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "pre-commit hooks installed (gitleaks runs on every commit)"
                $pass.Add("pre-commit hooks active")
            } else {
                Write-Warn "pre-commit install ran but reported an issue — check output"
                $warn.Add("pre-commit hooks may not be active")
            }
        } else {
            Write-Warn "Not a git repo — skipping pre-commit install"
            $warn.Add("pre-commit hooks not installed (no .git)")
        }
    } else {
        Write-Warn "pre-commit not installed — install manually: pip install pre-commit && pre-commit install"
        $warn.Add("pre-commit not installed")
    }
} else {
    Write-Warn ".pre-commit-config.yaml not found — skipping hook setup"
    $warn.Add(".pre-commit-config.yaml missing")
}

# ── 5. Template-mode exit ────────────────────────────────────────────────────
Write-Step 5 "Template-mode exit"

# These files must only exist in the Aptica repo-template itself.  GitHub's
# --template flag distributes ALL files, so every project repo receives them:
#   .is-template-repo       — boundary-hook sentinel (re-arms the boundary check)
#   .templatefiles          — boundary manifest (template-sync.ps1 reads it from
#                             the template remote, never the local copy)
#   .env.template           — template env scaffold (projects ship their own example)
# Remove them here (in project repos only) so the gates behave as designed.
$templateOnlyFiles = @(
    ".is-template-repo",
    ".templatefiles",
    ".env.template",
    # Legacy bypass sentinel. New template revisions no longer distribute it,
    # but remove it from projects initialized from an older revision.
    ".claude/no-survey-gate"
)

$remoteUrl = git remote get-url origin 2>$null
$canonicalTemplatePattern = '^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)(Aptica-Solutions/a-repo-template|szeltneraptica/repo-template)(\.git)?/?$'
$isTemplateItself = $remoteUrl -match $canonicalTemplatePattern

if ($isTemplateItself) {
    Write-Ok "This is the template repo — keeping template-only files"
    $pass.Add("template-only files retained (template repo)")
} else {
    $removed = [System.Collections.Generic.List[string]]::new()
    foreach ($rel in $templateOnlyFiles) {
        $filePath = Join-Path $repoRoot $rel
        if (-not (Test-Path $filePath)) { continue }
        if (Test-Path ".git") {
            git rm --quiet --force -- $rel 2>$null | Out-Null
            if ($LASTEXITCODE -ne 0) {
                # File exists on disk but not tracked — just delete it
                Remove-Item $filePath -Force
            }
        } else {
            Remove-Item $filePath -Force
        }
        $removed.Add($rel)
    }
    if ($removed.Count -gt 0) {
        Write-Ok "Removed template-only files: $($removed -join ', ')"
        $pass.Add("template-only files removed: $($removed -join ', ')")
    } else {
        Write-Ok "No template-only files present — already clean"
        $pass.Add("template-only files clean")
    }
}

# ── 7. Logging framework ─────────────────────────────────────────────────────
Write-Step 7 "Logging framework"

# Ensure base log directories exist (gitignored content, tracked via .md markers)
$logDirs = @("logs/dev-testing", "logs/test-case-1")
foreach ($ld in $logDirs) {
    $ldPath = Join-Path $repoRoot $ld
    if (-not (Test-Path $ldPath)) {
        New-Item -ItemType Directory -Path $ldPath -Force | Out-Null
        Write-Ok "Created $ld/"
    } else {
        Write-Ok "$ld/ exists"
    }
}
$pass.Add("Log directories ready")

# Verify python-json-logger is installed (required by _engineer/dev-env/log_util.py)
$pipCheck = & $venvPip show python-json-logger 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Ok "python-json-logger installed"
    $pass.Add("python-json-logger installed")
} else {
    Write-Host "  Installing python-json-logger..."
    & $venvPip install python-json-logger --quiet 2>&1 | Out-Null
    $pipCheck2 = & $venvPip show python-json-logger 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "python-json-logger installed"
        $pass.Add("python-json-logger installed")
    } else {
        Write-Warn "python-json-logger install failed — log_util.py will fall back to plain text"
        $warn.Add("python-json-logger not installed")
    }
}

# ── 8. Gitleaks secret scan ───────────────────────────────────────────────────
Write-Step 8 "Secret scan"

if (Test-Cmd "gitleaks") {
    Write-Host "  Scanning repository for secrets..."
    # Use --no-git for non-git repos; fall back to git-aware scan
    $scanArgs = if (Test-Path ".git") { @("detect", "--source", ".", "--verbose") } `
                else { @("detect", "--source", ".", "--no-git", "--verbose") }
    $scanOut = & gitleaks @scanArgs 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "No secrets detected"
        $pass.Add("gitleaks scan clean")
    } else {
        Write-Err "Potential secrets detected — review output below and rotate any real credentials"
        Write-Host $scanOut -ForegroundColor Red
        $fail.Add("gitleaks scan found issues")
    }
} else {
    Write-Warn "Skipping secret scan — gitleaks not available"
    $warn.Add("Secret scan skipped")
}

# ── 9. .env.example check ────────────────────────────────────────────────────
Write-Step 9 ".env setup"

if (Test-Path ".env") {
    Write-Ok ".env exists"
    $pass.Add(".env present")
} else {
    if (Test-Path ".env.example") {
        Write-Warn ".env not found — copy .env.example to .env and fill in values before running"
        Write-Host "  Run: Copy-Item .env.example .env" -ForegroundColor Yellow
        $warn.Add(".env not configured")
    } else {
        Write-Warn "Neither .env nor .env.example found"
        $warn.Add(".env.example missing")
    }
}

# ── Summary ──────────────────────────────────────────────────────────────────
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " Verification Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$pass | ForEach-Object { Write-Host "  PASS  $_" -ForegroundColor Green  }
$warn | ForEach-Object { Write-Host "  WARN  $_" -ForegroundColor Yellow }
$fail | ForEach-Object { Write-Host "  FAIL  $_" -ForegroundColor Red    }

Write-Host ""
if ($fail.Count -gt 0) {
    Write-Host "Some checks FAILED. Resolve the issues above before proceeding." -ForegroundColor Red
    exit 1
} elseif ($warn.Count -gt 0) {
    Write-Host "Environment ready with warnings. Review WARN items before production." -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "All checks passed. Environment is ready." -ForegroundColor Green
    exit 0
}
