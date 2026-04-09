# Runbook: Database Connection Pool Exhaustion

## Severity: HIGH
## Category: Database
## Services: Any service with database connections (PostgreSQL, MySQL, Redis)

## Symptoms
- Application errors: "too many connections" or "connection pool exhausted"
- Increasing request latency with CPU idle (off-CPU bottleneck)
- New requests queuing while existing connections are occupied
- Database shows max_connections approaching limit

## Diagnosis Steps

1. **Check application connection pool status:**
   ```bash
   kubectl exec -it <pod> -- ss -s
   kubectl exec -it <pod> -- ss -tn state established | grep :5432 | wc -l
   ```

2. **Check database-side connections:**
   ```sql
   -- PostgreSQL
   SELECT count(*), state FROM pg_stat_activity GROUP BY state;
   SELECT * FROM pg_stat_activity WHERE state = 'active' ORDER BY query_start;

   -- MySQL
   SHOW PROCESSLIST;
   SHOW STATUS LIKE 'Threads_connected';
   ```

3. **Check for slow queries holding connections:**
   ```sql
   -- PostgreSQL: queries running > 30 seconds
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query
   FROM pg_stat_activity
   WHERE state = 'active' AND now() - query_start > interval '30 seconds';
   ```

4. **Check Prometheus metrics:**
   ```promql
   # Connection pool utilization
   hikaricp_connections_active / hikaricp_connections_max
   # or for Python SQLAlchemy:
   sqlalchemy_pool_checked_out / sqlalchemy_pool_size
   ```

## Resolution

### Immediate
- Kill long-running queries:
  ```sql
  SELECT pg_terminate_backend(<pid>);
  ```
- Increase pool size temporarily (env var or config change)
- Restart affected pods to reset connection state
- Scale up replicas to distribute connections

### Root Cause Investigation
- Missing database indexes causing full table scans (slow queries hold connections)
- Connection leak: connections acquired but never returned to pool
- N+1 query pattern: each request opens many connections
- Lock contention: transactions holding locks too long
- Schema migration running during traffic hours

### Prevention
- Set connection pool size to: (number of cores * 2) + effective_spindle_count
- Configure connection timeout and idle timeout in pool settings
- Add connection pool utilization monitoring with alerts at 80%
- Use connection pooler like PgBouncer for PostgreSQL
- Run schema migrations during maintenance windows
