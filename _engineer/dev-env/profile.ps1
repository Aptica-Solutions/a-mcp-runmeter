# ==========================================================
# profile.ps1 - ultra-profile master loader
# Dot-sourced by the machine profile. Loads functions.ps1,
# wires up interactive shell features, and shows the help list.
# Add functions to functions.ps1, not here.
# ==========================================================

$ErrorActionPreference = 'Stop'

# VS Code shell integration - guard against loop: only source when VS Code's IPC
# hook is present, meaning code CLI talks to the running instance (no new window).
# Modern VS Code (1.80+) injects this automatically via VSCODE_INJECTION=1.
if ($env:TERM_PROGRAM -eq 'vscode' -and
    -not $env:VSCODE_INJECTION -and
    $env:VSCODE_IPC_HOOK_CLI -and
    (Get-Command code -ErrorAction SilentlyContinue)) {
    try { . "$(code --locate-shell-integration-path pwsh)" } catch { }
}

# Encoding consistency
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

# Load all functions
. (Join-Path $PSScriptRoot 'functions.ps1')

# PSReadLine - only when running interactively
if ($IsInteractive -and (Get-Module -ListAvailable -Name PSReadLine)) {
    Import-Module PSReadLine -ErrorAction SilentlyContinue | Out-Null
    Set-PSReadLineOption -PredictionSource HistoryAndPlugin
    Set-PSReadLineOption -PredictionViewStyle InlineView
    Set-PSReadLineKeyHandler -Key Alt+l -Function AcceptSuggestion
}

# Navigate to DEV_ROOT when set by a VS Code launcher script
if ($IsInteractive -and $env:DEV_ROOT -and (Test-Path -LiteralPath $env:DEV_ROOT)) {
    Set-Location $env:DEV_ROOT
}

# 1Password auto-signin
$env:OP_VAULT = 'code'
$null = Connect-OpSignin

# Show available functions and auth status
Show-ProfileHelp
Show-AuthStatus
