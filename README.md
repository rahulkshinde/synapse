# Synapse SRE Framework

A **private-first, VPC-ready** SRE Assistant framework that runs entirely within your VPC. Built with Python 3.11+, FastAPI, and LangChain, featuring automatic plugin discovery and privacy-first data processing.

## 🎯 Core Principles

- **Privacy-First**: All data is scrubbed through SecurityMiddleware before being sent to the local LLM
- **VPC-Ready**: Designed to run entirely within your private network
- **Plugin-First**: Simply drop a Python file into `/plugins` to extend functionality
- **Zero Configuration**: Plugins are automatically discovered and loaded

## 🏗️ Architecture

Synapse uses a **plugin-first architecture** where core functionality is defined through Abstract Base Classes (ABCs), and implementations are automatically discovered from the `/plugins` directory.

### System Architecture Diagram

```mermaid
flowchart LR
    subgraph aws_cloud["☁️ AWS Cloud"]
        direction TB
        CW[CloudWatch Alarms]
        PD[PagerDuty Webhook]
        EKS[EKS Metrics]
    end

    subgraph vpc_boundary["🛡️ Private VPC Boundary<br/>(Self-Hosted)"]
        direction TB
        CORE[Synapse Core<br/>FastAPI]
        SCRUB[PII Scrubber<br/>SecurityMiddleware]
        VDB[(Local Vector DB<br/>Qdrant/Chroma)]
        LLM[Local LLM<br/>Ollama/vLLM]
        
        CORE --> SCRUB
        SCRUB --> LLM
        CORE <--> VDB
        LLM --> CORE
    end

    subgraph gcp_cloud["☁️ GCP Cloud"]
        direction TB
        CM[Cloud Monitoring]
        PS[Pub/Sub]
        GKE[GKE Metrics]
    end

    subgraph extensions["🔌 Extensions"]
        CUSTOM[Custom Extension<br/>Python Plugin]
    end

    subgraph output_channels["📤 Output Channels"]
        direction TB
        SLACK[Slack]
        TEAMS[Microsoft Teams]
        JIRA[Jira]
    end

    CW -->|Alerts| CORE
    PD -->|Webhooks| CORE
    EKS -->|Metrics| CORE
    
    CM -->|Alerts| CORE
    PS -->|Events| CORE
    GKE -->|Metrics| CORE
    
    CUSTOM -->|Plugin API| CORE
    
    CORE -->|Incident Response| SLACK
    CORE -->|Notifications| TEAMS
    CORE -->|Tickets| JIRA

    classDef awsStyle fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:#fff
    classDef gcpStyle fill:#4285F4,stroke:#EA4335,stroke-width:2px,color:#fff
    classDef vpcStyle fill:#10B981,stroke:#059669,stroke-width:3px,color:#fff
    classDef extStyle fill:#8B5CF6,stroke:#6D28D9,stroke-width:2px,color:#fff
    classDef outStyle fill:#6366F1,stroke:#4F46E5,stroke-width:2px,color:#fff

    class CW,PD,EKS awsStyle
    class CM,PS,GKE gcpStyle
    class CORE,SCRUB,VDB,LLM vpcStyle
    class CUSTOM extStyle
    class SLACK,TEAMS,JIRA outStyle
```

### Architecture Overview

The diagram above illustrates how Synapse integrates with multiple cloud providers while maintaining complete data privacy within your VPC:

### Folder Structure

```
synapse/
├── core/                      # Core framework components
│   ├── base.py               # ABC interfaces (BaseMetrics, BaseKnowledge, BaseMessenger)
│   ├── plugin_loader.py      # Automatic plugin discovery system
│   ├── security.py          # SecurityMiddleware for PII/secret scrubbing
│   ├── orchestrator.py      # LangChain agent orchestration logic
│   └── schemas.py           # Pydantic v2 models
│
├── plugins/                  # Plugin implementations (auto-discovered)
│   ├── metrics/             # Metrics plugins (e.g., Prometheus, CloudWatch)
│   │   └── example_prometheus.py
│   ├── knowledge/           # Knowledge plugins (e.g., Confluence, Markdown)
│   └── messenger/           # Messenger plugins (e.g., Slack, MS Teams)
│       └── example_slack.py
│
├── app.py                    # FastAPI entry point
├── config.yaml              # Centralized configuration
├── docker-compose.yml        # VPC deployment configuration
└── requirements.txt          # Python dependencies
```

## ✨ Features

- **Automatic Plugin Discovery**: Drop a Python file implementing a base class into `/plugins` - it's automatically loaded
- **Privacy Layer**: SecurityMiddleware scrubs PII, secrets, API keys, and sensitive data before LLM processing
- **Local LLM Inference**: Uses Ollama with llama3.1 for completely private inference
- **LangChain Orchestration**: Intelligent agent that coordinates between metrics, knowledge, and messaging plugins
- **VPC Deployment**: Three-service Docker Compose setup (app, vector-db, inference-engine)

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Running with Docker Compose

1. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and set your SLACK_BOT_TOKEN
   ```

2. **Start services:**
   ```bash
   docker-compose up -d
   ```

This will start:
- **synapse-app**: FastAPI application (port 8000)
- **inference-engine**: Ollama with llama3.1 pre-loaded (port 11434)
- **vector-db**: ChromaDB for RAG (port 8001)

The inference engine automatically pulls `llama3.1` on first startup.

### Local Development

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app:app --reload
```

## 📡 API Endpoints

- `GET /` - API information
- `GET /health` - Health check with plugin status
- `GET /plugins` - List all discovered plugins
- `POST /webhook` - Generic webhook receiver
- `POST /incident` - PagerDuty webhook handler (processes incidents through orchestrator)
- `POST /incidents` - Create a new incident
- `POST /query` - Natural language query to the SRE assistant
- `POST /metrics/query` - Direct metrics query endpoint

## 🔌 Extending the Framework

### Creating a New Plugin

**It's as simple as dropping a Python file into the appropriate directory!**

#### Example: Creating a CloudWatch Metrics Plugin

1. Create `plugins/metrics/cloudwatch.py`:

```python
from typing import Any, Dict, List, Optional
from core.base import BaseMetrics

class CloudWatchMetrics(BaseMetrics):
    @property
    def name(self) -> str:
        return "cloudwatch"
    
    def get_metrics(
        self, query: str, start_time: Optional[str] = None, end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        # Your CloudWatch implementation here
        pass
    
    def list_available_metrics(self) -> List[str]:
        # List CloudWatch metrics
        pass
    
    def health_check(self) -> bool:
        # Check CloudWatch connectivity
        pass
```

2. **That's it!** The PluginLoader will automatically discover and register your plugin on startup.

#### Example: Creating a Confluence Knowledge Plugin

1. Create `plugins/knowledge/confluence.py`:

```python
from typing import Any, Dict, List, Optional
from core.base import BaseKnowledge

class ConfluenceKnowledge(BaseKnowledge):
    @property
    def name(self) -> str:
        return "confluence"
    
    def search(
        self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        # Your Confluence search implementation
        pass
    
    def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        # Retrieve Confluence page by ID
        pass
    
    def health_check(self) -> bool:
        # Check Confluence connectivity
        pass
```

2. The plugin is automatically available to the orchestrator!

#### Example: Creating an MS Teams Messenger Plugin

1. Create `plugins/messenger/teams.py`:

```python
from typing import Any, Dict, Optional
from core.base import BaseMessenger

class TeamsMessenger(BaseMessenger):
    @property
    def name(self) -> str:
        return "teams"
    
    def send_message(
        self, channel: str, message: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # Your Teams message implementation
        pass
    
    def send_alert(
        self, severity: str, title: str, description: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # Your Teams alert implementation
        pass
    
    def health_check(self) -> bool:
        # Check Teams connectivity
        pass
```

2. The orchestrator can now send alerts via Teams!

## 🔒 Privacy & Security

### SecurityMiddleware

All data is automatically scrubbed before being sent to the LLM. The SecurityMiddleware detects and redacts:

- API keys and tokens (Slack, AWS, etc.)
- Email addresses
- Credit card numbers
- SSNs
- Private IP addresses
- Database connection strings
- JWT tokens
- Custom patterns (configurable in `config.yaml`)

### Configuration

Add custom patterns in `config.yaml`:

```yaml
security:
  custom_patterns:
    custom_api_key: "api[_-]?key[=:]\s*([a-zA-Z0-9]{32})"
  enabled: true
  replacement: "[REDACTED]"
```

## ⚙️ Configuration

### config.yaml

Centralized configuration for VPC endpoints and plugin settings:

```yaml
llm:
  url: "http://ollama:11434"
  model: "llama3.1"

vector_db:
  type: "chromadb"
  host: "chromadb"
  port: 8000

plugins:
  metrics:
    prometheus:
      enabled: true
      base_url: "http://prometheus:9090"

vpc:
  prometheus: "http://prometheus:9090"
  chromadb: "http://chromadb:8000"
  ollama: "http://ollama:11434"
```

### Environment Variables

Some sensitive values should be set via environment variables:

```bash
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_DEFAULT_CHANNEL=#incidents
PROMETHEUS_URL=http://prometheus:9090
```

## 🔄 How It Works

1. **Plugin Discovery**: On startup, `PluginLoader` scans `/plugins` directory
2. **Automatic Registration**: Any class implementing `BaseMetrics`, `BaseKnowledge`, or `BaseMessenger` is registered
3. **Orchestrator Setup**: LangChain agent is created with tools from loaded plugins
4. **Privacy Scrubbing**: All data passes through `SecurityMiddleware` before LLM processing
5. **Local Inference**: Queries are sent to local Ollama instance (no external API calls)

## 📝 Example Usage

### Processing a PagerDuty Incident

```bash
curl -X POST http://localhost:8000/incident \
  -H "Content-Type: application/json" \
  -d '{
    "event": "incident.triggered",
    "incident": {
      "id": "P123456",
      "title": "High CPU Usage",
      "description": "CPU usage exceeded 90%",
      "severity": "high"
    }
  }'
```

The orchestrator will:
1. Query Prometheus for related metrics
2. Search knowledge base for runbooks
3. Generate recommendations using llama3.1
4. Send alert to Slack

### Natural Language Query

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the current CPU usage across all web servers?"}'
```

## 🐳 VPC Deployment

The `docker-compose.yml` creates a private network (`synapse-vpc`) with three services:

- **synapse-app**: Your FastAPI application
- **inference-engine**: Ollama with llama3.1
- **vector-db**: ChromaDB for RAG

All services communicate over the private network. Set `internal: true` in the network configuration for a fully isolated VPC.

## 📚 Base Classes Reference

### BaseMetrics

```python
class BaseMetrics(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @abstractmethod
    def get_metrics(query: str, start_time: str = None, end_time: str = None) -> List[Dict]: ...
    
    @abstractmethod
    def list_available_metrics(self) -> List[str]: ...
    
    @abstractmethod
    def health_check(self) -> bool: ...
```

### BaseKnowledge

```python
class BaseKnowledge(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @abstractmethod
    def search(query: str, limit: int = 10, filters: Dict = None) -> List[Dict]: ...
    
    @abstractmethod
    def get_by_id(item_id: str) -> Optional[Dict]: ...
    
    @abstractmethod
    def health_check(self) -> bool: ...
```

### BaseMessenger

```python
class BaseMessenger(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @abstractmethod
    def send_message(channel: str, message: str, metadata: Dict = None) -> Dict: ...
    
    @abstractmethod
    def send_alert(severity: str, title: str, description: str, metadata: Dict = None) -> Dict: ...
    
    @abstractmethod
    def health_check(self) -> bool: ...
```

## 🤝 Contributing

Contributions are welcome! To add a new plugin:

1. Implement the appropriate base class from `core.base`
2. Place your file in the appropriate `plugins/` subdirectory
3. The PluginLoader will automatically discover it
4. Submit a PR with your plugin implementation

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [LangChain](https://www.langchain.com/)
- [Ollama](https://ollama.ai/)
- [ChromaDB](https://www.trychroma.com/)
