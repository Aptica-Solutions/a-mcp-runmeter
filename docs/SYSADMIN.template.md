# SysAdmin Guide

> Audience: SysAdmins / IT Ops
> Purpose: Routine maintenance and basic troubleshooting

---

## Routine Maintenance

### Log Rotation

TODO: Describe log locations and rotation policy.

### Database Maintenance

TODO: Scheduled jobs, index rebuilds, backup verification.

### Certificate Renewal

TODO: Describe cert expiry monitoring and renewal process.

## Health Checks

TODO: Endpoints or scripts to verify system health.

```powershell
# Example health check
pwsh -NoProfile -Command "Invoke-RestMethod -Uri 'https://<app>/health'"
```

## Backup and Restore

TODO: Backup schedule, retention policy, restore procedure.

## Common Troubleshooting

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| App returns 503 | App Service stopped | Restart App Service in Azure Portal |
| Auth failures | Expired secret | Rotate secret in Key Vault, restart app |
| High latency | DB query | Check Application Insights slow query log |

## Escalation

If the issue is beyond routine ops, escalate to the engineering lead via the support channel listed in `README.md`.
