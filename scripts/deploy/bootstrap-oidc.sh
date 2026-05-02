#!/usr/bin/env bash
# bootstrap-oidc.sh — one-time creation of mi-bary-deploy and federated credentials.
# MUST be run by a human admin holding subscription Owner role via `az login` interactively.
# After this completes, every subsequent Azure deploy goes through GitHub Actions OIDC.
#
# Usage:
#   az login                # interactive
#   az account set --subscription <SUB_ID>
#   ./scripts/deploy/bootstrap-oidc.sh <github-org> <github-repo> [<location>]
#
# Defaults:
#   location = eastus2

set -euo pipefail

GITHUB_ORG="${1:-gravity}"
GITHUB_REPO="${2:-barycenter}"
LOCATION="${3:-eastus2}"

RG_IDENTITY="rg-barycenter-identity"
RG_DEV="rg-barycenter-dev"
MI_DEPLOY="mi-bary-deploy"
MI_WHATIF="mi-bary-whatif"

SUB_ID="$(az account show --query id -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"

echo "Subscription: $SUB_ID"
echo "Tenant:       $TENANT_ID"
echo "Org/repo:     ${GITHUB_ORG}/${GITHUB_REPO}"
echo "Location:     $LOCATION"
echo

# 1. Resource groups (idempotent)
for rg in "$RG_IDENTITY" "$RG_DEV"; do
  if ! az group show --name "$rg" >/dev/null 2>&1; then
    echo "Creating RG: $rg"
    az group create --name "$rg" --location "$LOCATION" >/dev/null
  else
    echo "RG exists:  $rg"
  fi
done

# 2. Managed identities
create_mi() {
  local name="$1"
  if ! az identity show --name "$name" --resource-group "$RG_IDENTITY" >/dev/null 2>&1; then
    echo "Creating MI: $name"
    az identity create --name "$name" --resource-group "$RG_IDENTITY" --location "$LOCATION" >/dev/null
  else
    echo "MI exists:  $name"
  fi
}
create_mi "$MI_DEPLOY"
create_mi "$MI_WHATIF"

DEPLOY_CLIENT_ID="$(az identity show --name "$MI_DEPLOY" --resource-group "$RG_IDENTITY" --query clientId -o tsv)"
DEPLOY_PRINCIPAL_ID="$(az identity show --name "$MI_DEPLOY" --resource-group "$RG_IDENTITY" --query principalId -o tsv)"
WHATIF_CLIENT_ID="$(az identity show --name "$MI_WHATIF" --resource-group "$RG_IDENTITY" --query clientId -o tsv)"
WHATIF_PRINCIPAL_ID="$(az identity show --name "$MI_WHATIF" --resource-group "$RG_IDENTITY" --query principalId -o tsv)"

# 3. Federated credentials — env-scoped per Pitfall 11; NO wildcards
create_fic() {
  local mi="$1" name="$2" subject="$3"
  if ! az identity federated-credential show --name "$name" --identity-name "$mi" --resource-group "$RG_IDENTITY" >/dev/null 2>&1; then
    echo "Creating FIC: $mi/$name (subject: $subject)"
    az identity federated-credential create \
      --name "$name" \
      --identity-name "$mi" \
      --resource-group "$RG_IDENTITY" \
      --issuer "https://token.actions.githubusercontent.com" \
      --subject "$subject" \
      --audience "api://AzureADTokenExchange" >/dev/null
  else
    echo "FIC exists:   $mi/$name"
  fi
}
create_fic "$MI_DEPLOY" "github-main"      "repo:${GITHUB_ORG}/${GITHUB_REPO}:ref:refs/heads/main"
create_fic "$MI_WHATIF" "github-pr-whatif" "repo:${GITHUB_ORG}/${GITHUB_REPO}:pull_request"

# 4. Role assignments — minimum required
assign_role() {
  local principal_id="$1" role="$2" scope="$3"
  if ! az role assignment list --assignee "$principal_id" --role "$role" --scope "$scope" --query "[0]" -o tsv | grep -q .; then
    echo "Granting $role to $principal_id at $scope"
    az role assignment create --assignee-object-id "$principal_id" --assignee-principal-type ServicePrincipal \
      --role "$role" --scope "$scope" >/dev/null
  else
    echo "Role exists: $role on $principal_id"
  fi
}
DEV_SCOPE="/subscriptions/${SUB_ID}/resourceGroups/${RG_DEV}"
assign_role "$DEPLOY_PRINCIPAL_ID" "Contributor"               "$DEV_SCOPE"
assign_role "$DEPLOY_PRINCIPAL_ID" "User Access Administrator" "$DEV_SCOPE"
assign_role "$WHATIF_PRINCIPAL_ID" "Reader"                    "$DEV_SCOPE"

# 5. Output (capture for evidence file + GitHub repo variables)
echo
echo "==== BOOTSTRAP COMPLETE ===="
echo "AZURE_TENANT_ID=${TENANT_ID}"
echo "AZURE_SUBSCRIPTION_ID=${SUB_ID}"
echo "AZURE_DEPLOY_CLIENT_ID=${DEPLOY_CLIENT_ID}"
echo "AZURE_WHATIF_CLIENT_ID=${WHATIF_CLIENT_ID}"
echo
echo "Next: set GitHub repo variables (NOT secrets — these are non-sensitive identifiers):"
echo "  gh variable set AZURE_TENANT_ID --body '${TENANT_ID}'"
echo "  gh variable set AZURE_SUBSCRIPTION_ID --body '${SUB_ID}'"
echo "  gh variable set AZURE_DEPLOY_CLIENT_ID --body '${DEPLOY_CLIENT_ID}'"
echo "  gh variable set AZURE_WHATIF_CLIENT_ID --body '${WHATIF_CLIENT_ID}'"
