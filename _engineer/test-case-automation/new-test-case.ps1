#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Scaffold a new test case directory structure.

.DESCRIPTION
  Creates tests/test-case-<Name>/{in,out}/ and logs/test-case-<Name>/
  with descriptive marker files. Also prints the .env.example lines to add.

.PARAMETER Name
  Test case identifier — used as the directory suffix.
  Examples: 2, "multi-page", "edge-case-empty"

.EXAMPLE
  pwsh -NoProfile -File tests/new-test-case.ps1 -Name 2
  pwsh -NoProfile -File tests/new-test-case.ps1 -Name "invoice-edge-case"
#>

param(
    [Parameter(Mandatory)]
    [string]$Name
)

$ErrorActionPreference = "Stop"

$slug     = "test-case-$Name"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

$testDir  = Join-Path $repoRoot "tests"  $slug
$inDir    = Join-Path $testDir "in"
$outDir   = Join-Path $testDir "out"
$logDir   = Join-Path $repoRoot "logs" $slug

function Write-Ok($msg)   { Write-Host "  OK    $msg" -ForegroundColor Green }
function Write-Skip($msg) { Write-Host "  SKIP  $msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "Scaffolding $slug" -ForegroundColor Cyan

# ── Test directories ──────────────────────────────────────────────────────────
foreach ($dir in @($inDir, $outDir, $logDir)) {
    if (Test-Path $dir) {
        Write-Skip "Already exists: $(Resolve-Path $dir -Relative -ErrorAction SilentlyContinue)"
    } else {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Ok "Created: $dir"
    }
}

# ── Marker files ──────────────────────────────────────────────────────────────
$markers = @{
    (Join-Path $inDir  "test-case-inputs.md")    = @"
# $slug — Inputs

Raw input files consumed by $slug. Add the source documents or data files exactly as the system under test will receive them.

Name files descriptively (e.g., ``invoice-multi-page.pdf``) so the test's intent is clear without reading the test code.
"@
    (Join-Path $outDir "expected-test-outputs.md") = @"
# $slug — Expected Outputs

Reference outputs the test runner diffs against. Treat these like any other assertion — review them in PRs and update intentionally, never silently.

Generate the initial outputs from a known-good run, then commit and lock them.
"@
    (Join-Path $logDir "$slug-logs.md")           = @"
# $slug — Logs

Log output produced when running $slug scenarios. Each run appends to (or replaces) the log file here.

Paired with ``tests/$slug/``. Set ``LOG_FILE=./logs/$slug/run.log`` when executing this test case.
"@
}

foreach ($path in $markers.Keys) {
    if (Test-Path $path) {
        Write-Skip "Already exists: $path"
    } else {
        Set-Content -Path $path -Value $markers[$path] -Encoding UTF8
        Write-Ok "Created: $path"
    }
}

# ── .env hint ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Add these lines to .env.example (and your .env):" -ForegroundColor Cyan
Write-Host ""
Write-Host "  # $slug" -ForegroundColor DarkGray
Write-Host "  PDF_INPUT_PATH_$(($Name.ToUpper() -replace '[^A-Z0-9]','_'))=./tests/$slug/in/sample.pdf"
Write-Host "  OUTPUT_DIR_$(($Name.ToUpper() -replace '[^A-Z0-9]','_'))=./tests/$slug/out"
Write-Host ""
Write-Host "  # When running $slug set:"
Write-Host "  LOG_FILE=./logs/$slug/run.log"
Write-Host ""
Write-Host "Done." -ForegroundColor Green
