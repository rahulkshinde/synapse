"""Synapse API. All data is scrubbed before reaching the LLM."""

import logging
import os
from typing import Any, Dict, List

import yaml
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from core.orchestrator import Orchestrator
from core.plugin_loader import PluginLoader
from core.schemas import Incident, MetricQuery, PagerDutyWebhook, WebhookPayload
from core.security import SecurityMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

config_path = os.getenv("CONFIG_PATH", "config.yaml")
config = {}
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}
else:
    logger.warning(f"Config file {config_path} not found, using defaults")

security = SecurityMiddleware(
    custom_patterns=config.get("security", {}).get("custom_patterns", {})
)

plugin_loader = PluginLoader(plugins_dir="plugins")

llm_config = config.get("llm", {})
orchestrator = Orchestrator(
    plugin_loader=plugin_loader,
    security=security,
    llm_url=os.getenv("OLLAMA_HOST", llm_config.get("url", "http://ollama:11434")),
    model_name=llm_config.get("model", "llama3.1"),
)

app_config = config.get("app", {})
app = FastAPI(
    title="Synapse SRE Framework",
    description="Private-first, VPC-ready SRE Assistant with plugin-first architecture",
    version="0.2.0",
    debug=app_config.get("debug", False),
)

if app_config.get("cors_enabled", False):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.get("cors_origins", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    response = await call_next(request)
    return response


@app.get("/")
async def root() -> Dict[str, str]:
    return {
        "name": "Synapse SRE Framework",
        "version": "0.2.0",
        "status": "operational",
        "architecture": "plugin-first",
        "privacy": "private-first",
    }


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    health = {
        "status": "healthy",
        "plugins": {
            "metrics": plugin_loader.list_metrics_plugins(),
            "knowledge": plugin_loader.list_knowledge_plugins(),
            "messenger": plugin_loader.list_messenger_plugins(),
        },
    }

    plugin_health = {}
    for name, plugin in plugin_loader.metrics_plugins.items():
        plugin_health[f"metrics.{name}"] = plugin.health_check()
    for name, plugin in plugin_loader.knowledge_plugins.items():
        plugin_health[f"knowledge.{name}"] = plugin.health_check()
    for name, plugin in plugin_loader.messenger_plugins.items():
        plugin_health[f"messenger.{name}"] = plugin.health_check()

    health["plugin_health"] = plugin_health
    return health


@app.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook(payload: WebhookPayload) -> Dict[str, Any]:
    logger.info(
        f"Received webhook: event_type={payload.event_type}, source={payload.source}"
    )

    try:
        result = await orchestrator.query(
            f"Process webhook event: {payload.event_type} from {payload.source}. "
            f"Data: {payload.data}"
        )

        return {
            "status": "accepted",
            "event_type": payload.event_type,
            "source": payload.source,
            "timestamp": payload.timestamp.isoformat(),
            "processing_result": result,
        }
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}",
        )


@app.post("/incident", status_code=status.HTTP_202_ACCEPTED)
async def handle_pagerduty_incident(webhook: PagerDutyWebhook) -> Dict[str, Any]:
    logger.info(
        f"Received PagerDuty webhook: event={webhook.event}, incident_id={webhook.incident.get('id')}"
    )

    try:
        incident_data = webhook.incident
        incident_title = incident_data.get("title", "Untitled Incident")
        incident_description = incident_data.get("description", "")
        incident_severity = incident_data.get("severity", "high")

        # Process through orchestrator
        result = await orchestrator.process_incident(
            incident_title=incident_title,
            incident_description=incident_description,
            severity=incident_severity,
        )

        return {
            "status": "processed",
            "incident_id": incident_data.get("id", "unknown"),
            "event": webhook.event,
            "orchestrator_result": result,
            "timestamp": incident_data.get("created_at", ""),
        }
    except Exception as e:
        logger.error(f"Error processing PagerDuty webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process incident: {str(e)}",
        )


@app.post("/incidents", status_code=status.HTTP_201_CREATED)
async def create_incident(incident: Incident) -> Dict[str, Any]:
    logger.info(f"Creating incident: {incident.title}")

    try:
        result = await orchestrator.process_incident(
            incident_title=incident.title,
            incident_description=incident.description,
            severity=incident.severity.value,
        )

        return {
            "status": "created",
            "incident": incident.model_dump(),
            "orchestrator_result": result,
        }
    except Exception as e:
        logger.error(f"Error creating incident: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create incident: {str(e)}",
        )


@app.post("/query", status_code=status.HTTP_200_OK)
async def query_assistant(query: str) -> Dict[str, Any]:
    try:
        result = await orchestrator.query(query)
        return result
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}",
        )


@app.post("/metrics/query")
async def query_metrics(query: MetricQuery) -> Dict[str, Any]:
    logger.info(f"Querying metrics: {query.query}")

    try:
        metrics_plugin = plugin_loader.get_metrics_plugin(query.provider)

        if not metrics_plugin:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No metrics plugin configured",
            )

        start_time_str = None
        end_time_str = None

        if query.start_time:
            start_time_str = query.start_time.isoformat()
        if query.end_time:
            end_time_str = query.end_time.isoformat()

        metrics = metrics_plugin.get_metrics(
            query=query.query,
            start_time=start_time_str,
            end_time=end_time_str,
        )

        scrubbed_metrics = security.scrub_list(metrics)

        return {
            "query": query.query,
            "plugin": metrics_plugin.name,
            "count": len(scrubbed_metrics),
            "metrics": scrubbed_metrics,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query metrics: {str(e)}",
        )


@app.get("/plugins")
async def list_plugins() -> Dict[str, List[str]]:
    return {
        "metrics": plugin_loader.list_metrics_plugins(),
        "knowledge": plugin_loader.list_knowledge_plugins(),
        "messenger": plugin_loader.list_messenger_plugins(),
    }


if __name__ == "__main__":
    import uvicorn

    host = app_config.get("host", "0.0.0.0")
    port = app_config.get("port", 8000)
    uvicorn.run(app, host=host, port=port)
