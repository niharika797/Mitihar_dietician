# Performance notes

Durable pointers on measured performance characteristics. Not a full investigation writeup —
see the linked PR/session for detail.

## Known Performance Hotspot — `/meal-plan/week`

**Finding:** under 1000-concurrent-user load (Run 4, 2026-08-07), the `weekly_combos` query behind
`GET /meal-plan/week` accounted for **~77% of top-5 query total time** in `pg_stat_statements` —
roughly 9x the next heaviest pattern. Three of the top 5 slow query patterns trace back to this
endpoint.

**Why:** suspected cause is the endpoint's `selectinload` fan-out, which materializes 84 combos
per patient per request. Not yet root-caused further than the query-pattern level.

**Where to look:** `pg_stat_statements` is enabled on staging (`mityahar-pg`) — it was **not**
enabled before 2026-08-07. Query it directly for future analysis:

```sql
SELECT query, calls, total_exec_time, mean_exec_time, max_exec_time
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

No need to re-enable it (confirmed no restart required to enable — Cloud SQL preloads it by
default). Reset with `SELECT pg_stat_statements_reset();` before a fresh measurement window if
old data would contaminate results.

**Not a current blocker:** Run 4 cleared both load-test abort conditions (error rate, sustained
p95) at 1000-user scale with this hotspot present. Flagging it as the first place to optimize
if load targets increase later, not a problem today.

Full context: [PR #7](https://github.com/niharika797/Mitihar_dietician/pull/7).
