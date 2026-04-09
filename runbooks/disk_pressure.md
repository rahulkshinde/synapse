# Runbook: Node Disk Pressure

## Severity: CRITICAL
## Category: Storage
## Services: All services on affected node

## Symptoms
- Node condition shows DiskPressure=True
- Pods being evicted from the node
- `kubectl describe node` shows "DiskPressure" taint
- Container image pulls failing with "no space left on device"

## Diagnosis Steps

1. **Identify affected nodes:**
   ```bash
   kubectl get nodes -o wide | grep -i "DiskPressure"
   kubectl describe node <node-name> | grep -A5 Conditions
   ```

2. **Check disk usage on the node:**
   ```bash
   # SSH to node or use node-shell
   df -h /
   df -h /var/lib/docker
   df -h /var/lib/kubelet
   ```

3. **Check for large container logs:**
   ```bash
   find /var/log/containers -size +100M -exec ls -lh {} \;
   ```

4. **Check for orphaned images and volumes:**
   ```bash
   docker system df    # or: crictl rmi --prune
   crictl images | wc -l
   ```

5. **Check Prometheus for disk trends:**
   ```promql
   node_filesystem_avail_bytes{mountpoint="/", instance=~"<node>.*"}
   / node_filesystem_size_bytes{mountpoint="/", instance=~"<node>.*"}
   ```

## Resolution

### Immediate
- Clean unused images: `crictl rmi --prune` or `docker system prune -af`
- Rotate large container logs: `truncate -s 0 /var/log/containers/<large-log>`
- Cordon the node to prevent new pods: `kubectl cordon <node>`
- If PVCs are full, expand the volume (EBS: modify volume size, then resize filesystem)

### Root Cause Investigation
- Application writing too many logs (missing log rotation config)
- Container images not being garbage collected (check kubelet gc thresholds)
- Emptydir volumes growing unbounded
- Failed image pulls leaving partial layers
- Prometheus TSDB or other stateful workloads consuming disk

### Prevention
- Set kubelet garbage collection: `imageGCHighThresholdPercent: 85`
- Configure log rotation in container runtime
- Set resource quotas for ephemeral storage
- Alert at 75% disk usage (warning) and 85% (critical)
- Use separate EBS volumes for /var/lib/docker
