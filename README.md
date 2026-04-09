<h1 align="center">Synapse</h1>

<p align="center">
  <strong>VPC-private AI SRE assistant — local LLM inference, zero data egress, plugin-first architecture</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License" /></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python" /></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://ollama.com/"><img src="https://img.shields.io/badge/Ollama-Local_LLM-000000" alt="Ollama" /></a>
</p>

<p align="center">
  <a href="#features">Features</a> &middot;
  <a href="#how-it-works">How It Works</a> &middot;
  <a href="#integrations">Integrations</a> &middot;
  <a href="#quick-start">Quick Start</a> &middot;
  <a href="#plugins">Plugins</a> &middot;
  <a href="#security--privacy">Security</a>
</p>

---

Synapse is an open-source (Apache 2.0) AI-powered SRE assistant that runs **entirely inside your VPC**. When a PagerDuty alert fires, Synapse's LangChain-orchestrated agent queries Prometheus for metrics, searches ChromaDB for matching runbooks, generates a root cause analysis via a **local Ollama LLM**, and posts remediation steps to Slack — all without a single byte leaving your network.

Unlike hosted AI copilots that send your incident data to third-party APIs, Synapse keeps **everything local**. Zero inference cost. Zero data egress. Zero vendor lock-in.

---

## Features

### Plugin-First Architecture

Drop a Python file into `/plugins` and it's live on next startup. No registration, no config changes, no restart scripts. The `PluginLoader` auto-discovers any class implementing `BaseMetrics`, `BaseKnowledge`, or `BaseMessenger`.

### PII & Secret Scrubbing

`SecurityMiddleware` runs 12+ regex patterns against all data **before** it reaches the LLM — AWS keys, Slack tokens, JWTs, emails, SSNs, credit cards, private IPs, database connection strings, and more. Custom patterns are supported via `config.yaml`.

### Local LLM Inference

Ollama runs inside the same Docker/Kubernetes network. No OpenAI API key. No per-token billing. No usage telemetry. The Helm chart's `NetworkPolicy` enforces **zero egress** from the LLM container after model pull.

### Knowledge Base RAG

ChromaDB-powered vector search over your runbooks, postmortems, and operational docs. The `seed_knowledge.py` script loads documents at init; the orchestrator queries them automatically during incident investigation.

### LangChain Orchestration

The agent dynamically selects tools — query metrics, search knowledge base, send alerts — based on the incident context. It correlates data across plugins and generates structured analysis with remediation steps.

### Additional Capabilities

- **Webhook Ingestion** — PagerDuty, generic webhooks, direct incident creation via REST API
- **Pydantic v2 Schemas** — Request/response validation with auto-generated OpenAPI docs
- **Health Probes** — `/health` endpoint reports per-plugin status for Kubernetes liveness/readiness
- **Helm Chart** — Production-ready Kubernetes deployment with persistence, resource limits, and NetworkPolicy
- **Docker Compose** — One-command local stack with all five services
- **Free Forever** — No per-seat or per-incident pricing. Apache 2.0

---

## How It Works

```text
Alert fires (PagerDuty, webhook, /incidents API)
        │
        ▼
   Synapse receives event
        │
        ▼
   SecurityMiddleware scrubs PII & secrets
        │
        ▼
   LangChain agent selects tools
        │
        ├── Queries Prometheus for related metrics
        ├── Searches ChromaDB knowledge base (RAG)
        └── Correlates data across plugins
                │
                ▼
   Local LLM generates analysis (Ollama)
        │
        ├── Root cause identification
        ├── Remediation recommendations
        └── Structured response with context
                │
                ▼
   Alert posted to Slack with analysis
```

---

## Integrations

| Category | Tools |
|----------|-------|
| **Metrics** | Prometheus, Node Exporter |
| **Knowledge** | ChromaDB (vector search), Markdown runbooks |
| **Messaging** | Slack |
| **Alerting** | PagerDuty (webhooks), generic webhooks |
| **LLM** | Ollama (local — llama3.1, llama3.2, any GGUF model) |
| **Deployment** | Docker Compose, Helm / Kubernetes |

> Synapse's plugin system makes it trivial to add CloudWatch, Datadog, Confluence, MS Teams, PagerDuty, or any other integration. Implement a base class, drop the file in `/plugins`, done.

---

## Quick Start

Get Synapse running locally:

```bash
# 1. Clone the repository
git clone https://github.com/your-org/synapse.git
cd synapse

# 2. Start all services
docker compose up -d

# 3. Pull a model into Ollama
docker compose exec ollama ollama pull llama3.2:1b

# 4. Seed runbooks into ChromaDB
pip install -r requirements.txt
python seed_knowledge.py --host localhost --port 8001

# 5. Run the demo
python demo_runner.py
```

**That's it!** The API is live at **http://localhost:8000**.

> **Note**: Synapse works with **zero external API keys**. Ollama runs locally. Cloud provider connectors and Slack are optional.

**Endpoints:**

| Service | Port | Purpose |
|---------|------|---------|
| **Synapse API** | 8000 | FastAPI application |
| **Ollama** | 11434 | Local LLM inference |
| **ChromaDB** | 8001 | Vector database for RAG |
| **Prometheus** | 9090 | Metrics collection |
| **Node Exporter** | 9100 | Host metrics |

To stop: `docker compose down` | Logs: `docker compose logs -f`

### Deploy on Kubernetes

```bash
helm install synapse ./charts/synapse \
  --set ollama.model="llama3.2:1b" \
  --set synapse.env.SLACK_BOT_TOKEN="xoxb-..." \
  --set networkPolicy.enabled=true
```

The Helm chart deploys all five components with configurable persistence, resource limits, health probes, and a `NetworkPolicy` that locks down Ollama to zero egress.

---

## Plugins

Synapse discovers plugins automatically. Implement one of three base classes and drop the file into the right directory.

```
plugins/
├── metrics/          BaseMetrics    (Prometheus, CloudWatch, Datadog)
├── knowledge/        BaseKnowledge  (ChromaDB, Confluence, Markdown)
└── messenger/        BaseMessenger  (Slack, Teams, PagerDuty)
```

### Writing a plugin

```python
# plugins/metrics/cloudwatch.py
from core.base import BaseMetrics

class CloudWatchMetrics(BaseMetrics):
    @property
    def name(self) -> str:
        return "cloudwatch"

    def get_metrics(self, query, start_time=None, end_time=None):
        ...

    def list_available_metrics(self):
        ...

    def health_check(self) -> bool:
        ...
```

No registration needed. The `PluginLoader` picks it up on next startup.

### Included plugins

| Plugin | Type | Dependency |
|--------|------|------------|
| **ExamplePrometheus** | Metrics | Prometheus server |
| **ChromaDBKnowledge** | Knowledge | ChromaDB (local or remote) |
| **ExampleSlack** | Messenger | `SLACK_BOT_TOKEN` env var |

---

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | API info |
| `GET` | `/health` | Health check with per-plugin status |
| `GET` | `/plugins` | List all discovered plugins |
| `POST` | `/incident` | PagerDuty webhook receiver |
| `POST` | `/incidents` | Create incident directly |
| `POST` | `/query` | Natural language SRE query |
| `POST` | `/webhook` | Generic webhook receiver |
| `POST` | `/metrics/query` | Direct Prometheus query |

### Example

```bash
curl -X POST http://localhost:8000/incident \
  -H "Content-Type: application/json" \
  -d '{
    "event": "incident.triggered",
    "incident": {
      "id": "P123456",
      "title": "High CPU on auth-api",
      "description": "CPU at 92% for 10 minutes",
      "severity": "high"
    }
  }'
```

Synapse queries Prometheus for related metrics, searches ChromaDB for matching runbooks, generates a remediation plan via the local LLM, and posts the analysis to Slack.

---

## Architecture

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.11+, FastAPI, LangChain |
| **LLM** | Ollama (local inference) |
| **Vector Store** | ChromaDB |
| **Metrics** | Prometheus, Node Exporter |
| **Messaging** | Slack (via Bot API) |
| **Validation** | Pydantic v2 |
| **Deployment** | Docker Compose, Helm / Kubernetes |

```text
synapse/
├── app.py                  # FastAPI entry point
├── config.yaml             # Service configuration
├── docker-compose.yml      # Local development stack
├── Dockerfile              # Multi-stage production build
├── seed_knowledge.py       # Load runbooks into ChromaDB
├── demo_runner.py          # End-to-end demo script
├── core/
│   ├── base.py             # Plugin interfaces (ABCs)
│   ├── orchestrator.py     # LangChain agent + tools
│   ├── plugin_loader.py    # Auto-discovery engine
│   ├── schemas.py          # Pydantic request/response models
│   └── security.py         # PII/secret scrubbing
├── plugins/
│   ├── metrics/            # Prometheus plugin
│   ├── knowledge/          # ChromaDB plugin
│   └── messenger/          # Slack plugin
├── charts/synapse/         # Helm chart
├── tests/                  # pytest suite
└── runbooks/               # SRE runbooks (seeded into ChromaDB)
```

---

## Security & Privacy

Synapse is fully self-hosted — **your incident data never leaves your environment**.

- All data stays on your infrastructure (Docker Compose or Kubernetes)
- No telemetry or usage data sent anywhere
- `SecurityMiddleware` scrubs PII/secrets before any LLM call
- Kubernetes `NetworkPolicy` enforces zero egress from Ollama after model pull
- Ollama runs locally — no third-party LLM API calls, no data sharing
- Custom scrubbing patterns supported via `config.yaml`

### Scrubbing coverage

| Category | Patterns |
|----------|----------|
| **Cloud Credentials** | AWS access keys, AWS secret keys |
| **Tokens** | Slack (`xoxb-`/`xoxp-`), JWTs, bearer tokens, API keys |
| **PII** | Email addresses, SSNs, credit card numbers |
| **Infrastructure** | Private IPs (RFC 1918), database connection strings |
| **Secrets** | Passwords in `key=value` format, custom regex patterns |

---

## Configuration

### Environment variables

```bash
OLLAMA_HOST=http://ollama:11434
PROMETHEUS_URL=http://prometheus:9090
CHROMA_HOST=chromadb
CHROMA_PORT=8000
SLACK_BOT_TOKEN=xoxb-your-token       # optional
SLACK_DEFAULT_CHANNEL=#incidents       # optional
```

### config.yaml

```yaml
llm:
  url: "http://ollama:11434"
  model: "llama3.1"
  temperature: 0.1

plugins:
  metrics:
    prometheus:
      enabled: true
      base_url: "http://prometheus:9090"
  messenger:
    slack:
      enabled: true
      bot_token: "${SLACK_BOT_TOKEN}"
      default_channel: "#incidents"

security:
  custom_patterns: {}
  enabled: true
  replacement: "[REDACTED]"
```

---

## Testing

```bash
pip install -r requirements.txt
pytest tests/ -v
```

50 tests cover SecurityMiddleware patterns, plugin discovery, ChromaDB operations, and API endpoint validation — all without requiring Ollama or external services.

---

## Contributing

Contributions welcome! To add a new plugin:

1. Implement `BaseMetrics`, `BaseKnowledge`, or `BaseMessenger` from `core.base`
2. Place the file in the appropriate `plugins/` subdirectory
3. The `PluginLoader` auto-discovers it on startup
4. Submit a PR

---

## License

Apache License 2.0. See [LICENSE](LICENSE).

---

<p align="center">
  <strong>If Synapse helps your team, give it a star!</strong>
</p>
