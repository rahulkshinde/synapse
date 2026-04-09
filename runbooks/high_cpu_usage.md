# Runbook: High CPU Usage

## Severity: HIGH
## Category: Compute
## Services: Any service with CPU-based autoscaling

## Symptoms
- CPU utilization > 85% sustained for > 5 minutes
- Pod restarts due to OOMKill or CPU throttling
- Increased request latency (p99 > 2x baseline)
- HPA scaling events firing rapidly

## Diagnosis Steps

1. **Identify the hot pods:**
   ```bash
   kubectl top pods -n <namespace> --sort-by=cpu
   ```

2. **Check if HPA is scaling:**
   ```bash
   kubectl get hpa -n <namespace>
   kubectl describe hpa <hpa-name> -n <namespace>
   ```

3. **Check for CPU throttling:**
   ```promql
   rate(container_cpu_cfs_throttled_seconds_total{namespace="<ns>"}[5m])
   ```

4. **Look for recent deployments:**
   ```bash
   kubectl rollout history deployment/<name> -n <namespace>
   ```

5. **Check for runaway queries or goroutine leaks:**
   - Review application logs for stack traces
   - Check thread/goroutine count metrics

## Resolution

### Immediate
- Scale up replicas manually if HPA is slow: `kubectl scale deployment/<name> --replicas=<N>`
- If a single pod is the outlier, delete it: `kubectl delete pod <pod-name>`
- Check if CPU requests/limits are set too low

### Root Cause Investigation
- Review recent code changes for O(n²) algorithms or missing pagination
- Check for connection pool exhaustion causing retry storms
- Verify cron jobs or batch processes aren't overlapping
- Look for missing indexes in database queries causing full table scans

### Prevention
- Set CPU requests to match p95 usage, limits to 2x requests
- Configure HPA with `stabilizationWindowSeconds: 0` for fast scale-up
- Add CPU throttling alerts before hitting OOM thresholds
