-- Engineering-intelligence queries over Wynxx SDLC execution records.
-- Replace `project.wynxx_observability.tool_executions` with your table.
-- These power the Looker dashboard that turns "developers are using AI" into
-- the leadership view from the article.

-- 1) Portfolio summary (last 30 days) ---------------------------------------
SELECT
  COUNTIF(tool = 'wynxx.analyze_repository' AND status = 'success')      AS repositories_analyzed,
  COUNTIF(tool = 'wynxx.generate_tests' AND status = 'success')          AS test_runs,
  COUNTIF(tool = 'wynxx.generate_documentation_draft' AND status = 'success') AS docs_generated,
  COUNTIF(tool = 'wynxx.modernization_assessment' AND status = 'success')     AS modernization_assessments,
  COUNTIF(model_armor_verdict = 'block')                                 AS model_armor_blocks
FROM `project.wynxx_observability.tool_executions`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY);

-- 2) Adoption by team / tenant ----------------------------------------------
SELECT
  tenant_id,
  COUNT(DISTINCT user_id)        AS active_users,
  COUNT(*)                       AS tool_calls,
  COUNT(DISTINCT repository)     AS repositories_touched
FROM `project.wynxx_observability.tool_executions`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY tenant_id
ORDER BY tool_calls DESC;

-- 3) Latency and reliability by tool ----------------------------------------
SELECT
  tool,
  COUNT(*)                                          AS calls,
  ROUND(AVG(duration_ms))                           AS avg_ms,
  APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)]    AS p95_ms,
  SAFE_DIVIDE(COUNTIF(status = 'failed'), COUNT(*)) AS failure_rate
FROM `project.wynxx_observability.tool_executions`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY tool
ORDER BY calls DESC;

-- 4) Modernization candidates (repos most assessed) -------------------------
SELECT
  repository,
  COUNT(*) AS assessments,
  MAX(timestamp) AS last_assessed
FROM `project.wynxx_observability.tool_executions`
WHERE tool = 'wynxx.modernization_assessment'
  AND status = 'success'
GROUP BY repository
ORDER BY assessments DESC
LIMIT 25;
