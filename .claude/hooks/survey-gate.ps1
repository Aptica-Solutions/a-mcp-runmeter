#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Claude Code UserPromptSubmit hook — survey gate.

.DESCRIPTION
  Runs before every user prompt. If ONBOARDING.md is missing or empty, injects a
  blocking message into the conversation context so Claude refuses to do project
  work until the survey is complete.

  Once the survey is signed off in a repo, a completion marker
  (_engineer/.onboarding-complete) is written. When that marker is present the
  hook exits immediately and never gates again, so sign-off is a one-time event.

  Output on stdout is injected as system context by Claude Code.
  Exit 0 = allow (with optional context injection).
  Exit 2 = hard block (prompt is rejected outright).
#>

# Skip the gate only in the canonical template checkout. GitHub template creation
# copies .is-template-repo into downstream repositories until initialization removes
# it, so the marker alone is not sufficient evidence.
$repoRoot = git rev-parse --show-toplevel 2>$null
$isGitRepository = $LASTEXITCODE -eq 0 -and $repoRoot

if ($isGitRepository) {
    $templateMarker = Join-Path $repoRoot ".is-template-repo"
    $originUrl = git -C $repoRoot remote get-url origin 2>$null
    $canonicalTemplatePattern = '^(https://github\.com/|git@github\.com:|ssh://git@github\.com/)(Aptica-Solutions/a-repo-template|szeltneraptica/repo-template)(\.git)?/?$'

    if ((Test-Path $templateMarker) -and $originUrl -match $canonicalTemplatePattern) {
        exit 0
    }
}

if (-not $isGitRepository) {
    $repoRoot = (Get-Location).Path
}

# One-time sign-off: once the onboarding survey is signed off in this repo, the
# gate is retired for good. Sign-off is recorded by this marker, written at the
# end of /project-init. To sign off manually: `touch _engineer/.onboarding-complete`.
# To re-enable the gate: delete the marker. Committing the marker retires the gate
# repo-wide; add it to .gitignore instead to make sign-off per-developer.
$completionMarker = Join-Path $repoRoot "_engineer/.onboarding-complete"
if (Test-Path $completionMarker) {
    exit 0
}
$onboardingPath = Join-Path $repoRoot "ONBOARDING.md"

$missing = -not (Test-Path $onboardingPath)
$empty   = -not $missing -and (Get-Item $onboardingPath).Length -eq 0

if ($missing -or $empty) {
    Write-Output @"
ONBOARDING GATE — ACTION REQUIRED

ONBOARDING.md is $(if ($missing) { "missing" } else { "empty" }). You must not:
- Write or modify any code
- Create or delete project files
- Plan architecture or design systems
- Run project scripts or install dependencies
- Make any task list or requirements decisions

Respond to the user with exactly this message:
"ONBOARDING.md not found. I cannot begin any project work until the survey is complete. Please run /project-init to walk through the survey, or confirm that ONBOARDING.md exists and is accurate."

Answering general questions about the template structure or how tools work is permitted. All project-specific work is blocked.
"@
}

# Exit 0 in both cases — hard block (exit 2) would prevent even the warning from showing.
exit 0
