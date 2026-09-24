<#
.SYNOPSIS
    PowerShell compatibility wrapper for the CodeQL-scannable Python template sync CLI.

.DESCRIPTION
    Preserves the established PowerShell interface while delegating all template
    synchronization, merge, lock, and path-validation behavior to template_sync.py.
    The default mode remains a read-only dry run.

.EXAMPLE
    pwsh -NoProfile -File _engineer/dev-env/template-sync.ps1 `
      -TemplateRef template-v2026.07.1 -Profile standard

.EXAMPLE
    pwsh -NoProfile -File _engineer/dev-env/template-sync.ps1 `
      -TemplateRef template-v2026.07.1 -Profile standard `
      -AcceptExistingAsBaseline -Apply
#>

[CmdletBinding()]
param(
    [string]$TemplateRemote = "template",
    [string]$TemplateRef = "main",
    [ValidateSet("standard", "standard-local-docs", "nested-template", "lightweight", "exempt")]
    [string]$Profile = "standard",
    [string]$TemplateRelease = "",
    [string]$LockPath = ".aptica/template-lock.json",
    [string]$ReportPath = "",
    [switch]$AcceptExistingAsBaseline,
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-PythonCommand {
    <#
    .SYNOPSIS
        Return the path of a usable Python 3 interpreter, or throw.

    .DESCRIPTION
        macOS and most Linux distributions ship only `python3`; Windows ships
        `python` and reserves `python3` for a Store stub that opens a browser
        when nothing is installed. The wrapper therefore prefers the name each
        platform actually provides and falls back to the other, so no caller
        has to shim a `python` symlink onto PATH before running the sync.
        APTICA_PYTHON overrides both, for pinned or virtualenv interpreters.
    #>
    $override = [System.Environment]::GetEnvironmentVariable("APTICA_PYTHON")
    if ($override) {
        if (-not (Test-Path -LiteralPath $override -PathType Leaf)) {
            throw "APTICA_PYTHON is set but does not resolve to a file: $override"
        }
        return $override
    }
    $isWindowsHost = [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform(
        [System.Runtime.InteropServices.OSPlatform]::Windows)
    $candidates = if ($isWindowsHost) { @("python", "python3") } else { @("python3", "python") }
    foreach ($name in $candidates) {
        $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($command) {
            return $command.Source
        }
    }
    throw "No Python interpreter found on PATH (tried: $($candidates -join ', ')). Set APTICA_PYTHON to override."
}

$python = Resolve-PythonCommand
$pythonScript = Join-Path $PSScriptRoot "template_sync.py"
if (-not (Test-Path -LiteralPath $pythonScript -PathType Leaf)) {
    throw "Template sync engine not found: $pythonScript"
}

$pythonArguments = @(
    $pythonScript,
    "--template-remote", $TemplateRemote,
    "--template-ref", $TemplateRef,
    "--profile", $Profile,
    "--lock-path", $LockPath
)

if ($TemplateRelease) {
    $pythonArguments += @("--template-release", $TemplateRelease)
}
if ($ReportPath) {
    $pythonArguments += @("--report-path", $ReportPath)
}
if ($AcceptExistingAsBaseline) {
    $pythonArguments += "--accept-existing-as-baseline"
}
if ($Apply) {
    $pythonArguments += "--apply"
}

& $python @pythonArguments
exit $LASTEXITCODE
