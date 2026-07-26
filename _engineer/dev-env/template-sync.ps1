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
    [ValidateSet("standard", "nested-template", "lightweight", "exempt")]
    [string]$Profile = "standard",
    [string]$TemplateRelease = "",
    [string]$LockPath = ".aptica/template-lock.json",
    [string]$ReportPath = "",
    [switch]$AcceptExistingAsBaseline,
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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

& python @pythonArguments
exit $LASTEXITCODE
