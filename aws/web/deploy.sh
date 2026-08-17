#!/usr/bin/env bash
#
# Build the Storage Browser app and deploy it to the CloudFront-fronted S3 bucket.
# Reads all configuration from `terraform output`, so run `terraform apply` first.
#
# Usage:
#   ./deploy.sh                 # uses the default AWS profile
#   AWS_PROFILE=myprofile ./deploy.sh
#
# Requires: terraform, node/npm, aws CLI, jq.

set -euo pipefail

WEB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="${WEB_DIR}/../terraform"

echo "==> Reading Terraform outputs"
# Tolerate missing/null outputs so we can print a friendly error below
# instead of dying on terraform's raw error under `set -e`.
tf() { terraform -chdir="${TF_DIR}" output -raw "$1" 2>/dev/null || true; }

REGION="$(tf region)"
USER_POOL_ID="$(tf cognito_user_pool_id)"
USER_POOL_CLIENT_ID="$(tf cognito_user_pool_client_id)"
IDENTITY_POOL_ID="$(tf cognito_identity_pool_id)"
COGNITO_DOMAIN="$(tf cognito_domain)"
OIDC_PROVIDER="$(tf oidc_provider_name)"
UPLOAD_BUCKET="$(tf upload_bucket_name)"
DOWNLOAD_BUCKET="$(tf download_bucket_name)"
WEBAPP_BUCKET="$(tf webapp_bucket_name)"
DISTRIBUTION_ID="$(tf webapp_cloudfront_distribution_id)"

if [[ -z "${USER_POOL_ID}" || "${USER_POOL_ID}" == "null" ]]; then
  echo "ERROR: Storage Browser outputs are empty. Set enable_storage_browser = true and apply first." >&2
  exit 1
fi

echo "==> Writing .env"
cat > "${WEB_DIR}/.env" <<EOF
VITE_AWS_REGION=${REGION}
VITE_USER_POOL_ID=${USER_POOL_ID}
VITE_USER_POOL_CLIENT_ID=${USER_POOL_CLIENT_ID}
VITE_IDENTITY_POOL_ID=${IDENTITY_POOL_ID}
VITE_COGNITO_DOMAIN=${COGNITO_DOMAIN}
VITE_OIDC_PROVIDER=${OIDC_PROVIDER}
VITE_UPLOAD_BUCKET=${UPLOAD_BUCKET}
VITE_DOWNLOAD_BUCKET=${DOWNLOAD_BUCKET}
EOF

echo "==> Building"
cd "${WEB_DIR}"
npm ci
npm run build

echo "==> Syncing to s3://${WEBAPP_BUCKET}"
aws s3 sync dist "s3://${WEBAPP_BUCKET}" --delete

echo "==> Invalidating CloudFront ${DISTRIBUTION_ID}"
aws cloudfront create-invalidation --distribution-id "${DISTRIBUTION_ID}" --paths "/*" >/dev/null

echo "==> Done: $(tf storage_browser_url)"
