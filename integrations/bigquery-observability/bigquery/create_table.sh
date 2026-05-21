#!/usr/bin/env bash
#
# Create the BigQuery sink for Wynxx SDLC execution records.
#
# The table is partitioned by day on `timestamp` and clustered by tenant/tool
# for cheap, fast queries over high-volume agent telemetry.
#
# Usage:
#   PROJECT_ID=my-project ./create_table.sh
#
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
DATASET="${DATASET:-wynxx_observability}"
TABLE="${TABLE:-tool_executions}"
LOCATION="${LOCATION:-US}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA="${SCRIPT_DIR}/schema.json"

echo ">> Ensuring dataset ${PROJECT_ID}:${DATASET} (${LOCATION})"
bq --project_id="${PROJECT_ID}" --location="${LOCATION}" mk --dataset --force "${DATASET}" || true

echo ">> Creating table ${PROJECT_ID}:${DATASET}.${TABLE}"
bq --project_id="${PROJECT_ID}" mk --table \
  --time_partitioning_field timestamp \
  --time_partitioning_type DAY \
  --clustering_fields tenant_id,tool \
  "${DATASET}.${TABLE}" \
  "${SCHEMA}"

echo
echo ">> Done. Point your Cloud Logging sink / ADK BigQuery Agent Analytics"
echo "   plugin at ${PROJECT_ID}:${DATASET}.${TABLE}, then build the Looker view"
echo "   from analytics.sql."
