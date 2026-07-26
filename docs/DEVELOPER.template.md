# Developer Reference

> Audience: Software Engineers
> Purpose: Deep technical specification — architecture, APIs, data models, dev setup

---

## Architecture

TODO: High-level diagram and description of components, data flow, and boundaries.

## Local Development Setup

```powershell
# Prerequisites: Node 20+, Python 3.11+, pwsh 7+, op CLI

# 1. Clone
pwsh -NoProfile -Command "git clone <repo-url>"
pwsh -NoProfile -Command "Set-Location <repo>"

# 2. Install dependencies
pwsh -NoProfile -Command "Set-Location backend; npm install"
pwsh -NoProfile -Command "Set-Location ../frontend; npm install"

# 3. Configure environment
pwsh -NoProfile -Command "Copy-Item .env.example .env"
# Fill in values — or use op run

# 4. Start
# TODO: pwsh -NoProfile -Command "npm run dev"
```

## API Reference

TODO: Document endpoints, request/response shapes, auth requirements.

## Data Models

TODO: Key entities and their schemas.

## Key Design Decisions

TODO: Document non-obvious architectural choices and why they were made.

## Environment Variables

See `.env.example` for the full list with descriptions.

## Testing

```powershell
# Unit tests
pwsh -NoProfile -Command "npm test"

# Integration tests
pwsh -NoProfile -Command "npm run test:integration"

# Coverage report
pwsh -NoProfile -Command "npm run test:coverage"
```
