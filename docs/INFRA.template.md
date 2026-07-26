# Infrastructure

> Audience: Platform Engineers
> Purpose: Infrastructure design, deployment, scalability, and security planning

---

## Architecture Overview

TODO: Diagram and description of Azure resources used.

## Bicep Templates

| Template | Purpose |
|----------|---------|
| `infra-setup/bicep/keyvault.bicep` | Azure Key Vault with access policies |
| `infra-setup/bicep/document-intelligence.bicep` | Azure AI Document Intelligence account |

## Terraform Templates

| Template Set | Purpose |
|--------------|---------|
| `infra-setup/tera/*.tf` | Terraform equivalent for Key Vault + Document Intelligence |

## Deployment

```powershell
# Set variables
pwsh -NoProfile -Command "$rg = 'rg-intelligent-automation'; $location = 'eastus'; az deployment group create --resource-group $rg --template-file infra-setup/bicep/keyvault.bicep --parameters infra-setup/bicep/keyvault.bicepparam"

# Deploy Key Vault
pwsh -NoProfile -Command "$rg = 'rg-intelligent-automation'; az deployment group create --resource-group $rg --template-file infra-setup/bicep/document-intelligence.bicep --parameters infra-setup/bicep/document-intelligence.bicepparam"
```

## Resource Tagging

All resources must be tagged:

| Tag | Values |
|-----|--------|
| `env` | dev · test · prod |
| `app` | [application name] |
| `entity` | client-a · client-b · client-c |
| `workload` | [workload name] |

## Security Design

- All secrets in Key Vault — no secrets in ARM/Bicep parameters files committed to source
- Managed Identity used for service-to-service auth (no client secrets)
- Private endpoints for all PaaS services in production
- Network Security Groups on all subnets

## Scalability Notes

TODO: Scaling triggers, limits, and recommendations.

## Cost Management

- Cost alerts configured at 80% and 100% of budget
- Resources tagged for cost attribution
- Auto-shutdown enabled for non-production compute
