# Synapse Demo - Private AI SRE Assistant

**Note:** This demo has been consolidated into `synapse_mvd.py`. See [MVD_README.md](./MVD_README.md) for the latest demo documentation.

A minimalist demonstration of the Synapse SRE Assistant workflow: **PagerDuty Alert → Prometheus → Ollama → Slack**.

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Docker and Docker Compose (for running services locally)

### 2. Start Required Services

#### Option A: Using Docker Compose (Recommended)

```bash
# Start Prometheus and Ollama
docker-compose -f docker-compose.mvd.yml up -d

# Pull the llama3.1 model
docker exec ollama-mvd ollama pull llama3.1
```

#### Option B: Manual Docker Commands

**Start Prometheus:**

```bash
docker run -d \
  --name prometheus-demo \
  -p 9090:9090 \
  -v $(pwd)/prometheus-demo.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus:latest
```

**Start Ollama:**

```bash
docker run -d \
  --name ollama-demo \
  -p 11434:11434 \
  -v ollama-data:/root/.ollama \
  ollama/ollama:latest

# Pull the model
docker exec ollama-demo ollama pull llama3.1
```

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
# Prometheus configuration
PROMETHEUS_URL=http://localhost:9090

# Ollama configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1

# Slack configuration (optional - script will skip if not set)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
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
2. **Fetches Metrics**: Queries Prometheus for `node_cpu_seconds_total` (with mock data fallback)
3. **Processes with AI**: Sends the metric data to local Ollama (llama3.1) for analysis
4. **Notifies Slack**: Posts formatted alert with AI analysis to Slack

## Example Output

```
🚀 Synapse SRE Assistant Demo
==================================================

1️⃣  Fetching metrics from http://localhost:9090...
   ✅ Metrics fetched successfully

2️⃣  Processing with Ollama (llama3.1)...
   ✅ Analysis complete

3️⃣  Sending to Slack...
   ✅ Analysis sent to Slack successfully

✨ Demo complete!
```

## Troubleshooting

### Prometheus Not Running

```
❌ Error fetching metrics from Prometheus: Connection refused
   Make sure Prometheus is running at http://localhost:9090
```

**Solution**: Start Prometheus using Docker (see above) or ensure your Prometheus instance is accessible.

### Ollama Not Running

```
❌ Error calling Ollama: Connection refused
   Make sure Ollama is running at http://localhost:11434
   And that model 'llama3.1' is available (run: ollama pull llama3.1)
```

**Solution**: 
1. Start Ollama: `docker run -d -p 11434:11434 ollama/ollama`
2. Pull model: `docker exec ollama-demo ollama pull llama3.1`

### Model Not Found

If you get an error about the model not being available:

```bash
# Pull the model
docker exec ollama-demo ollama pull llama3.1

# Or use a different model by setting OLLAMA_MODEL in .env
```

### Slack Webhook Not Configured

If `SLACK_WEBHOOK_URL` is not set, the script will print the analysis to stdout instead of sending to Slack.

## Customization

### Change the Metric Query

Edit `synapse_mvd.py` and modify the query in `fetch_prometheus_metrics()`:

```python
query = "up"  # Or any PromQL query
```

### Use a Different LLM Model

Set `OLLAMA_MODEL` in your `.env` file:

```bash
OLLAMA_MODEL=llama3.2  # or mistral, codellama, etc.
```

Make sure to pull the model first:

```bash
docker exec ollama-demo ollama pull llama3.2
```

## Quick Test

After starting services, verify they're running:

```bash
# Check Prometheus
curl http://localhost:9090/api/v1/query?query=up

# Check Ollama
curl http://localhost:11434/api/tags
```

## Notes

- The script is intentionally minimal (< 100 lines) for demonstration purposes
- All processing happens locally - no external API calls (except Slack webhook)
- The script includes basic error handling for common issues
- Prometheus and Ollama must be running before executing the script
