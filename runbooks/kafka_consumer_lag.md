# Runbook: Kafka Consumer Lag

## Severity: HIGH
## Category: Event Streaming
## Services: Any Kafka consumer group (MSK, Strimzi, Confluent)

## Symptoms
- Consumer lag growing steadily (messages produced > messages consumed)
- Downstream services showing stale data
- DataDog/Prometheus alerts on consumer_lag metric
- End-user impact: delayed event processing, stale dashboards

## Diagnosis Steps

1. **Check consumer group lag:**
   ```bash
   kafka-consumer-groups.sh --bootstrap-server <broker>:9092 \
     --describe --group <consumer-group>
   # Look at LAG column — should be near 0 for healthy consumers
   ```

2. **Check if consumers are running:**
   ```bash
   kubectl get pods -n <namespace> -l app=<consumer-app>
   kubectl logs -f <consumer-pod> -n <namespace> --tail=100
   ```

3. **Check Prometheus metrics:**
   ```promql
   # Consumer lag by topic and group
   kafka_consumergroup_lag{consumergroup="<group>", topic="<topic>"}

   # Consumer processing rate
   rate(kafka_consumer_records_consumed_total{group="<group>"}[5m])
   ```

4. **Check if brokers are healthy:**
   ```promql
   kafka_server_replicamanager_underreplicatedpartitions
   # Should be 0. Non-zero means broker issues.
   ```

5. **Check for slow downstream dependencies:**
   - Database queries slowing consumer processing
   - External API calls timing out
   - Disk I/O on broker nodes

## Resolution

### Immediate
- Scale up consumer pods: `kubectl scale deployment/<consumer> --replicas=<N>`
- Ensure number of consumers <= number of partitions (extra consumers are idle)
- If a single partition is lagging, check for a poison message (large or malformed)
- Reset consumer offset if processing stale data is acceptable:
  ```bash
  kafka-consumer-groups.sh --bootstrap-server <broker>:9092 \
    --group <group> --topic <topic> --reset-offsets --to-latest --execute
  ```

### Root Cause Investigation
- Consumer processing too slow (optimize message handling, batch processing)
- Too few partitions for the throughput needed (repartition topic)
- Broker disk I/O bottleneck (check EBS throughput on MSK nodes)
- Rebalancing storms: consumers joining/leaving frequently
- Network issues between consumers and brokers

### Prevention
- Use KEDA ScaledObject to auto-scale consumers based on lag
- Set consumer lag alerts: warning at 1000, critical at 10000
- Monitor consumer commit rate alongside lag
- Size partitions to match expected peak throughput
- Use Cruise Control for broker rebalancing
