"""LangChain agent orchestrator. Coordinates plugins, scrubs data, invokes local LLM."""

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from pydantic import ConfigDict

from core.plugin_loader import PluginLoader
from core.security import SecurityMiddleware

logger = logging.getLogger(__name__)


class MetricsTool(BaseTool):

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "query_metrics"
    description: str = (
        "Query metrics from monitoring systems. Use this to fetch current or historical metric data."
    )
    metrics_plugin: Any = None
    security: Any = None

    def _run(
        self,
        query: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> str:
        try:
            metrics = self.metrics_plugin.get_metrics(query, start_time, end_time)
            scrubbed_metrics = self.security.scrub_list(metrics)
            import json

            return json.dumps(scrubbed_metrics, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error querying metrics: {str(e)}")
            return f"Error querying metrics: {str(e)}"

    async def _arun(
        self,
        query: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> str:
        return self._run(query, start_time, end_time)


class KnowledgeTool(BaseTool):

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "search_knowledge"
    description: str = (
        "Search the knowledge base for documentation, runbooks, or troubleshooting guides."
    )
    knowledge_plugin: Any = None
    security: Any = None

    def _run(self, query: str, limit: int = 5) -> str:
        try:
            results = self.knowledge_plugin.search(query, limit=limit)
            scrubbed_results = self.security.scrub_list(results)
            import json

            return json.dumps(scrubbed_results, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error searching knowledge: {str(e)}")
            return f"Error searching knowledge: {str(e)}"

    async def _arun(self, query: str, limit: int = 5) -> str:
        return self._run(query, limit)


class MessengerTool(BaseTool):

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "send_alert"
    description: str = (
        "Send an alert or message to communication channels. Use this to notify teams about incidents or findings."
    )
    messenger_plugin: Any = None
    security: Any = None

    def _run(
        self,
        severity: str,
        title: str,
        description: str,
        channel: Optional[str] = None,
        metadata: Optional[str] = None,
    ) -> str:
        try:
            import json

            meta_dict = json.loads(metadata) if metadata else {}
            scrubbed_meta = self.security.scrub_dict(meta_dict)
            scrubbed_desc = self.security.scrub(description)

            result = self.messenger_plugin.send_alert(
                severity=severity,
                title=title,
                description=scrubbed_desc,
                metadata=scrubbed_meta,
            )

            if channel:
                self.messenger_plugin.send_message(
                    channel=channel,
                    message=f"{title}\n{scrubbed_desc}",
                    metadata=scrubbed_meta,
                )

            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error sending alert: {str(e)}")
            return f"Error sending alert: {str(e)}"

    async def _arun(
        self,
        severity: str,
        title: str,
        description: str,
        channel: Optional[str] = None,
        metadata: Optional[str] = None,
    ) -> str:
        return self._run(severity, title, description, channel, metadata)


class Orchestrator:

    def __init__(
        self,
        plugin_loader: PluginLoader,
        security: SecurityMiddleware,
        llm_url: str = "http://ollama:11434",
        model_name: str = "llama3.1",
    ):
        self.plugin_loader = plugin_loader
        self.security = security
        self.llm = ChatOllama(base_url=llm_url, model=model_name, temperature=0.1)

        self.tools: List[BaseTool] = []
        self._build_tools()
        self.agent = self._create_agent()

    def _build_tools(self):
        metrics_plugin = self.plugin_loader.get_metrics_plugin()
        if metrics_plugin:
            self.tools.append(
                MetricsTool(metrics_plugin=metrics_plugin, security=self.security)
            )
            logger.info("Added metrics tool to agent")

        knowledge_plugin = self.plugin_loader.get_knowledge_plugin()
        if knowledge_plugin:
            self.tools.append(
                KnowledgeTool(knowledge_plugin=knowledge_plugin, security=self.security)
            )
            logger.info("Added knowledge tool to agent")

        messenger_plugin = self.plugin_loader.get_messenger_plugin()
        if messenger_plugin:
            self.tools.append(
                MessengerTool(messenger_plugin=messenger_plugin, security=self.security)
            )
            logger.info("Added messenger tool to agent")

        if not self.tools:
            logger.warning("No plugins loaded - agent will have no tools")

    def _create_agent(self) -> AgentExecutor:
        system_prompt = """You are an SRE Assistant helping with incident response and system reliability.

Your capabilities:
- Query metrics from monitoring systems
- Search knowledge bases for runbooks and documentation
- Send alerts and notifications to teams

Always follow these principles:
1. Use metrics to understand the current state of systems
2. Search knowledge base for relevant runbooks before taking action
3. Provide clear, actionable recommendations
4. Escalate critical issues immediately via alerts

When analyzing incidents:
- Gather relevant metrics first
- Search for similar past incidents or runbooks
- Provide a summary with recommended actions
- Send alerts for critical issues"""

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = create_openai_functions_agent(self.llm, self.tools, prompt)
        return AgentExecutor(agent=agent, tools=self.tools, verbose=True)

    async def process_incident(
        self, incident_title: str, incident_description: str, severity: str = "high"
    ) -> Dict[str, Any]:
        scrubbed_title = self.security.scrub(incident_title)
        scrubbed_description = self.security.scrub(incident_description)

        query = f"""Incident detected:
Title: {scrubbed_title}
Severity: {severity}
Description: {scrubbed_description}

Please:
1. Query relevant metrics to understand the current system state
2. Search the knowledge base for relevant runbooks or similar incidents
3. Provide a summary with recommended actions
4. If severity is critical or high, send an alert with the findings"""

        try:
            start_ts = time.monotonic()
            result = await self.agent.ainvoke({"input": query, "chat_history": []})
            elapsed = time.monotonic() - start_ts
            self._audit_log(
                "incident", query, result.get("output", ""), elapsed, severity
            )
            return {
                "status": "processed",
                "response": result.get("output", ""),
                "scrubbed": True,
            }
        except Exception as e:
            logger.error(f"Error processing incident: {str(e)}", exc_info=True)
            self._audit_log("incident", query, f"ERROR: {e}", 0.0, severity)
            return {
                "status": "error",
                "error": str(e),
            }

    async def query(self, user_query: str) -> Dict[str, Any]:
        scrubbed_query = self.security.scrub(user_query)

        try:
            start_ts = time.monotonic()
            result = await self.agent.ainvoke(
                {"input": scrubbed_query, "chat_history": []}
            )
            elapsed = time.monotonic() - start_ts
            self._audit_log("query", scrubbed_query, result.get("output", ""), elapsed)
            return {
                "status": "success",
                "response": result.get("output", ""),
                "scrubbed": True,
            }
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            self._audit_log("query", scrubbed_query, f"ERROR: {e}", 0.0)
            return {
                "status": "error",
                "error": str(e),
            }

    def _audit_log(
        self,
        query_type: str,
        scrubbed_input: str,
        output_summary: str,
        elapsed_seconds: float,
        severity: str = "info",
    ):
        input_hash = hashlib.sha256(scrubbed_input.encode()).hexdigest()[:16]
        tools_available = [t.name for t in self.tools]
        entry = {
            "audit": "synapse_llm_query",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query_type": query_type,
            "severity": severity,
            "input_hash": input_hash,
            "input_length": len(scrubbed_input),
            "output_length": len(output_summary),
            "elapsed_seconds": round(elapsed_seconds, 3),
            "tools_available": tools_available,
            "scrubbed": True,
        }
        logger.info(json.dumps(entry))
