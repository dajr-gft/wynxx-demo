#!/usr/bin/env bash
#
# Deploy the Wynxx MCP server to Cloud Run with authentication enforced.
#
# This is the expanded form of the article's deploy snippet. The
# `--no-allow-unauthenticated` flag is NOT optional: Agent Gateway reaches the
# service over an authenticated channel; the service is never public.
#
# Usage:
#   PROJECT_ID=my-project ./deploy.sh
#
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-wynxx-mcp-server}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-wynxx-mcp@${PROJECT_ID}.iam.gserviceaccount.com}"
WYNXX_MODE="${WYNXX_MODE:-stub}"

echo ">> Deploying ${SERVICE_NAME} to ${REGION} (project ${PROJECT_ID}, mode=${WYNXX_MODE})"

# Optional one-time setup (uncomment on first run):
# gcloud iam service-accounts create wynxx-mcp \
#   --project="${PROJECT_ID}" \
#   --display-name="Wynxx MCP server"

gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --source . \
  --region "${REGION}" \
  --no-allow-unauthenticated \
  --service-account "${SERVICE_ACCOUNT}" \
  --set-env-vars "WYNXX_MODE=${WYNXX_MODE},WYNXX_MCP_SERVER_ID=wynxx-sdlc" \
  --port 8080

echo
echo ">> Deployed. The MCP endpoint is the service URL with the /mcp path:"
URL="$(gcloud run services describe "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" --region "${REGION}" \
  --format='value(status.url)')"
echo "   ${URL}/mcp"
echo
echo ">> Next: register it in Agent Registry — see ../agent-gateway-governance/register-mcp-server.sh"
