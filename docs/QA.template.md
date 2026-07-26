# QA Guide

> Audience: QA Engineers
> Purpose: Manual and automated testing instructions

---

## Test Environment Setup

TODO: Steps to spin up a clean test environment.

## Automated Tests

```powershell
# All tests
pwsh -NoProfile -Command "npm test"

# Integration only
pwsh -NoProfile -Command "npm run test:integration"

# Coverage
pwsh -NoProfile -Command "npm run test:coverage"

# Security scan
pwsh -NoProfile -Command "npm audit"
```

## Manual Test Cases

### Happy Path
TODO: List steps for the primary user workflow.

### Edge Cases
TODO: Boundary conditions, empty states, large inputs.

### Security Test Cases
- [ ] Verify `.env` is not accessible via any HTTP endpoint
- [ ] Confirm auth tokens are not logged in plain text
- [ ] Test rate limiting on public endpoints
- [ ] Verify CORS rejects unauthorized origins
- [ ] Confirm PHI does not appear in logs

### Accessibility
- [ ] Keyboard navigation works throughout the application
- [ ] Screen reader announces dynamic content updates
- [ ] Color contrast meets WCAG 2.1 AA minimum
- [ ] All form fields have accessible labels

## Regression Checklist

Run before every release:
- [ ] All automated tests passing
- [ ] Security scan clean (gitleaks, npm audit)
- [ ] Manual happy path verified
- [ ] Settings page saves and persists correctly

> *(Include if: ONBOARDING "Auth" = Entra / OAuth. Delete if not applicable.)*
- [ ] OAuth flow works end-to-end
