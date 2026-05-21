#!/usr/bin/env bash
#
# Publish the Wynxx SDLC API as a governed MCP tool through an Apigee MCP proxy.
#
# Mechanics (from Google's documentation, as described in the article):
#   1. Create an MCP proxy in an environment group.
#   2. Use `/mcp` as the basepath.
#   3. Point the target to `mcp.apigee.internal`.
#   4. Attach this OpenAPI spec — Apigee uses its operations as the tools list.
#   5. Deploy. The proxy is auto-registered in Apigee API hub.
#
# This script wraps those steps with `apigeecli`. Exact subcommand flags can
# vary with the apigeecli / Apigee version; the Console flow in README.md mirrors
# these same steps if you prefer the UI.
#
# Prereqs: apigeecli (https://github.com/apigee/apigeecli), gcloud, an Apigee
# org with an environment + environment group.
#
# Usage:
#   PROJECT_ID=my-project APIGEE_ENV=eval APIGEE_ENVGROUP=eval-group ./deploy-apigee.sh
#
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
APIGEE_ENV="${APIGEE_ENV:?Set APIGEE_ENV (e.g. eval)}"
APIGEE_ENVGROUP="${APIGEE_ENVGROUP:?Set APIGEE_ENVGROUP (e.g. eval-group)}"
PROXY_NAME="${PROXY_NAME:-wynxx-mcp}"
BASEPATH="${BASEPATH:-/mcp}"
MCP_TARGET="${MCP_TARGET:-mcp.apigee.internal}"
SPEC="${SPEC:-wynxx-openapi.yaml}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEC_PATH="${SCRIPT_DIR}/${SPEC}"

echo ">> Validating OpenAPI spec: ${SPEC_PATH}"
if command -v openapi-spec-validator >/dev/null 2>&1; then
  openapi-spec-validator "${SPEC_PATH}"
else
  echo "   (openapi-spec-validator not installed; skipping local validation)"
fi

TOKEN="$(gcloud auth print-access-token)"

echo ">> Creating MCP proxy '${PROXY_NAME}' (basepath ${BASEPATH}, target ${MCP_TARGET})"
# Generate an MCP proxy bundle from the OpenAPI spec and import it. The proxy
# exposes MCP at BASEPATH and routes to the Apigee MCP runtime target.
apigeecli apis create openapi \
  --name "${PROXY_NAME}" \
  --oas-file "${SPEC_PATH}" \
  --basepath "${BASEPATH}" \
  --target-url "https://${MCP_TARGET}" \
  --add-cors=false \
  --org "${PROJECT_ID}" \
  --token "${TOKEN}"

echo ">> Deploying '${PROXY_NAME}' to env '${APIGEE_ENV}'"
apigeecli apis deploy \
  --name "${PROXY_NAME}" \
  --env "${APIGEE_ENV}" \
  --ovr \
  --wait \
  --org "${PROJECT_ID}" \
  --token "${TOKEN}"

HOSTNAME="$(apigeecli envgroups get \
  --name "${APIGEE_ENVGROUP}" --org "${PROJECT_ID}" --token "${TOKEN}" \
  --disable-check 2>/dev/null | grep -oE '"hostnames":\s*\[[^]]*' | grep -oE 'https?://[^",]+' | head -n1 || true)"
HOSTNAME="${HOSTNAME:-https://<your-env-group-hostname>}"

echo
echo ">> Done. MCP endpoint (any compliant MCP client can call tools/list here):"
echo "   ${HOSTNAME}${BASEPATH}"
echo
echo ">> The proxy is auto-registered in Apigee API hub. Next: register it in"
echo "   Agent Registry — see ../agent-gateway-governance/register-mcp-server.sh"
