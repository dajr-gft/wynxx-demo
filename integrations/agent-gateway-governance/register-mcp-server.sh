#!/usr/bin/env bash
#
# Register the Wynxx MCP server in Agent Registry.
#
# This is the central library of approved MCP servers that every consumer
# surface (Gemini CLI, Code Assist, ADK, Gemini Enterprise) discovers tools
# through. Registration is the prerequisite for Agent Gateway to govern calls to
# the server.
#
# Works for either path:
#   * Path A — endpoint is your Cloud Run service URL + /mcp
#   * Path B — endpoint is your Apigee env-group host + /mcp
#
# Usage:
#   PROJECT_ID=my-project \
#   ENDPOINT_URL=https://wynxx-mcp-server-xxxxx.run.app/mcp \
#   ./register-mcp-server.sh
#
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
LOCATION="${LOCATION:-us-central1}"
MCP_SERVER_ID="${MCP_SERVER_ID:-wynxx-sdlc}"
ENDPOINT_URL="${ENDPOINT_URL:?Set ENDPOINT_URL (the .../mcp endpoint)}"
DESCRIPTION="${DESCRIPTION:-Enterprise SDLC automation tools}"

echo ">> Registering MCP server '${MCP_SERVER_ID}' in Agent Registry"
echo "   project=${PROJECT_ID} location=${LOCATION}"
echo "   endpoint=${ENDPOINT_URL}"

gcloud agent-platform registry mcp-servers create "${MCP_SERVER_ID}" \
  --project="${PROJECT_ID}" \
  --location="${LOCATION}" \
  --endpoint-url="${ENDPOINT_URL}" \
  --description="${DESCRIPTION}"

echo
echo ">> Registered. Verify with:"
echo "   gcloud agent-platform registry mcp-servers describe ${MCP_SERVER_ID} \\"
echo "     --project=${PROJECT_ID} --location=${LOCATION}"
echo
echo ">> Next: grant a specific agent identity egress to it —"
echo "   ./scripts/grant_agent_mcp_egress.sh --mcp ${MCP_SERVER_ID} --agent-id sdlc-orchestrator-agent"
