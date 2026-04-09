# Runbook: OOMKilled Pod

## Severity: HIGH
## Category: Memory
## Services: Any containerized service

## Symptoms
- Pod status shows OOMKilled in `kubectl describe pod`
- Container restarts with exit code 137
- Memory usage approaching container limits
- Application becomes unresponsive before restart

## Diagnosis Steps

1. **Confirm OOMKill:**
   ```bash
   kubectl describe pod <pod-name> -n <namespace> | grep -A5 "Last State"
   # Look for: Reason: OOMKilled, Exit Code: 137
   ```

2. **Check current memory usage vs limits:**
   ```bash
   kubectl top pods -n <namespace> --sort-by=memory
   kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].resources}'
   ```

3. **Check memory usage over time:**
   ```promql
   container_memory_working_set_bytes{namespace="<ns>", pod=~"<pod-pattern>.*"}
   / container_spec_memory_limit_bytes{namespace="<ns>", pod=~"<pod-pattern>.*"}
   ```

4. **Check for memory leaks (trending upward over hours):**
   ```promql
   rate(container_memory_working_set_bytes{pod=~"<pattern>.*"}[1h])
   ```

## Resolution

### Immediate
- Increase memory limits in the deployment spec
- Restart the pod if memory leak is suspected: `kubectl delete pod <pod>`
- Check if JVM heap is misconfigured (Java apps): `-Xmx` should be 75% of container limit

### Root Cause Investigation
- Memory leak: Check for unclosed connections, growing caches, or unbounded buffers
- Burst traffic: Check if memory scales with request count (consider request-based autoscaling)
- Large payloads: Check for oversized request/response bodies
- For Python: Check for circular references preventing garbage collection
- For Go: Use `pprof` heap profile to identify allocations

### Prevention
- Set memory requests to p95 usage, limits to 1.5x requests
- Add memory usage alerts at 80% of limit (warning) and 90% (critical)
- Implement graceful degradation (shed load before OOM)
- Use VPA (Vertical Pod Autoscaler) recommendations for right-sizing
