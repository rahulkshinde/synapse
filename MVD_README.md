# Synapse MVD - Minimum Viable Demo

A bare-minimum local demo script showcasing Synapse's troubleshooting loop: **PagerDuty Alert → Prometheus → Ollama AI → Slack**.

## Quick Start

### 1. Start Services

```bash
docker-compose -f docker-compose.mvd.yml up -d
```

### 2. Pull Ollama Model

```bash
docker exec ollama-mvd ollama pull llama3.1
```

### 3. Configure Environment

```bash
cp .env.example.mvd .env
# Edit .env and add your SLACK_WEBHOOK_URL (optional)
```

### 4. Install Dependencies

```bash
pip install -r mvd_requirements.txt
```

### 5. Run the Demo

```bash
python synapse_mvd.py
```

## What It Does

1. **Mocks PagerDuty Alert**: Simulates "High CPU on Service-A" incident
2. **Fetches Metrics**: Queries Prometheus for `node_cpu_seconds_total`
   - Falls back to mock data if Prometheus is unreachable
3. **AI Analysis**: Uses Ollama (llama3.1) to analyze metrics and suggest resolution
4. **Slack Notification**: Sends formatted alert with AI analysis to Slack

## Example Output

```
🚀 Synapse MVD - Troubleshooting Loop

==================================================

1️⃣  Simulating PagerDuty alert...
   Alert: High CPU on Service-A
   Service: Service-A

2️⃣  Fetching Prometheus metrics...
   ✅ Metrics retrieved

3️⃣  Analyzing with Ollama (llama3.1)...
   ✅ Analysis complete

4️⃣  Sending to Slack...
   ✅ Analysis sent to Slack

==================================================
✨ Troubleshooting loop complete!
```

## Configuration

### Environment Variables

Create a `.env` file:

```bash
PROMETHEUS_URL=http://localhost:9090
OLLAMA_MODEL=llama3.1
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Without Slack

If `SLACK_WEBHOOK_URL` is not set, the script will print the analysis to stdout instead.

## Troubleshooting

### Prometheus Unreachable

The script automatically falls back to mock metric data if Prometheus is unreachable, so the demo will still work.

### Ollama Not Running

```bash
# Start Ollama
docker-compose -f docker-compose.mvd.yml up -d ollama

# Pull model
docker exec ollama-mvd ollama pull llama3.1
```

### Model Not Found

```bash
# List available models
docker exec ollama-mvd ollama list

# Pull the model
docker exec ollama-mvd ollama pull llama3.1
```

## Extending the Script

The script is designed to be easily extended by SREs:

- **Change the alert**: Modify `mock_pagerduty_alert()` function
- **Query different metrics**: Update the query in `fetch_prometheus_metrics()`
- **Customize AI prompt**: Modify the system/user prompts in `analyze_with_ai()`
- **Add more services**: Extend the mock data or add real service discovery

## Files

- `synapse_mvd.py` - Main demo script
- `docker-compose.mvd.yml` - Docker Compose configuration
- `.env.example.mvd` - Environment variable template
- `mvd_requirements.txt` - Python dependencies
