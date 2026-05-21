#!/usr/bin/env bash
#
# Grant a named agent identity egress permission to call a named MCP server.
#
# This is the command that matters most for a CISO review: an explicit grant
# from one named Agent Identity to one named MCP server — recorded, auditable,
# and revocable. Agent Gateway enforces this binding on every egress call.
#
# Usage:
#   ./grant_agent_mcp_egress.sh --mcp wynxx-sdlc --agent-id sdlc-orchestrator-agent
#
# Optional flags:
#   --project   GCP project id              (default: $PROJECT_ID env)
#   --location  region                      (default: us-central1)
#   --revoke    remove the grant instead of adding it
#
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-}"
LOCATION="us-central1"
MCP_SERVER_ID=""
AGENT_ID=""
ACTION="grant"

usage() {
  grep '^#' "$0" | sed 's/^#//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mcp)       MCP_SERVER_ID="$2"; shift 2 ;;
    --agent-id)  AGENT_ID="$2"; shift 2 ;;
    --project)   PROJECT_ID="$2"; shift 2 ;;
    --location)  LOCATION="$2"; shift 2 ;;
    --revoke)    ACTION="revoke"; shift ;;
    -h|--help)   usage 0 ;;
    *) echo "Unknown argument: $1" >&2; usage 1 ;;
  esac
done

: "${PROJECT_ID:?Set --project or PROJECT_ID}"
: "${MCP_SERVER_ID:?Set --mcp}"
: "${AGENT_ID:?Set --agent-id}"

echo ">> ${ACTION^} egress: agent '${AGENT_ID}' -> MCP server '${MCP_SERVER_ID}'"
echo "   project=${PROJECT_ID} location=${LOCATION}"

if [[ "${ACTION}" == "grant" ]]; then
  gcloud agent-platform gateway egress-bindings create \
    --project="${PROJECT_ID}" \
    --location="${LOCATION}" \
    --agent-id="${AGENT_ID}" \
    --mcp-server="${MCP_SERVER_ID}" \
    --mode=egress
else
  gcloud agent-platform gateway egress-bindings delete \
    --project="${PROJECT_ID}" \
    --location="${LOCATION}" \
    --agent-id="${AGENT_ID}" \
    --mcp-server="${MCP_SERVER_ID}"
fi

echo
echo ">> Done. The binding is recorded and visible in Cloud Audit Logs."
echo "   Agent Gateway will enforce it on every call from '${AGENT_ID}'."
