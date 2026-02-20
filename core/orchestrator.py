"""LangChain agent orchestrator for SRE workflows.

This module implements the core orchestration logic using LangChain to coordinate
between metrics plugins, knowledge plugins, and messenger plugins. All data
is scrubbed through the SecurityMiddleware before being sent to the local LLM.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama

from core.base import BaseKnowledge, BaseMessenger, BaseMetrics
from core.plugin_loader import PluginLoader
from core.security import SecurityMiddleware

logger = logging.getLogger(__name__)


class MetricsTool(BaseTool):
    """LangChain tool for querying metrics."""

    name: str = "query_metrics"
    description: str = "Query metrics from monitoring systems. Use this to fetch current or historical metric data."

    def __init__(self, metrics_plugin: BaseMetrics, security: SecurityMiddleware):
        """Initialize the metrics tool.
        
        Args:
            metrics_plugin: Metrics plugin instance
            security: Security middleware for scrubbing
        """
        super().__init__()
        self.metrics_plugin = metrics_plugin
        self.security = security

    def _run(self, query: str, start_time: Optional[str] = None, end_time: Optional[str] = None) -> str:
        """Execute the metrics query.
        
        Args:
            query: Metric query string
            start_time: Optional start time (ISO 8601)
            end_time: Optional end time (ISO 8601)
            
        Returns:
            JSON string of metric results (scrubbed)
        """
        try:
            metrics = self.metrics_plugin.get_metrics(query, start_time, end_time)
            # Scrub sensitive data before returning
            scrubbed_metrics = self.security.scrub_list(metrics)
            import json
            return json.dumps(scrubbed_metrics, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error querying metrics: {str(e)}")
            return f"Error querying metrics: {str(e)}"

    async def _arun(self, query: str, start_time: Optional[str] = None, end_time: Optional[str] = None) -> str:
        """Async version of metrics query."""
        return self._run(query, start_time, end_time)


class KnowledgeTool(BaseTool):
    """LangChain tool for searching knowledge base."""

    name: str = "search_knowledge"
    description: str = "Search the knowledge base for documentation, runbooks, or troubleshooting guides."

    def __init__(self, knowledge_plugin: BaseKnowledge, security: SecurityMiddleware):
        """Initialize the knowledge tool.
        
        Args:
            knowledge_plugin: Knowledge plugin instance
            security: Security middleware for scrubbing
        """
        super().__init__()
        self.knowledge_plugin = knowledge_plugin
        self.security = security

    def _run(self, query: str, limit: int = 5) -> str:
        """Execute the knowledge search.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            JSON string of search results (scrubbed)
        """
        try:
            results = self.knowledge_plugin.search(query, limit=limit)
            # Scrub sensitive data before returning
            scrubbed_results = self.security.scrub_list(results)
            import json
            return json.dumps(scrubbed_results, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error searching knowledge: {str(e)}")
            return f"Error searching knowledge: {str(e)}"

    async def _arun(self, query: str, limit: int = 5) -> str:
        """Async version of knowledge search."""
        return self._run(query, limit)


class MessengerTool(BaseTool):
    """LangChain tool for sending messages/alerts."""

    name: str = "send_alert"
    description: str = "Send an alert or message to communication channels. Use this to notify teams about incidents or findings."

    def __init__(self, messenger_plugin: BaseMessenger, security: SecurityMiddleware):
        """Initialize the messenger tool.
        
        Args:
            messenger_plugin: Messenger plugin instance
            security: Security middleware for scrubbing
        """
        super().__init__()
        self.messenger_plugin = messenger_plugin
        self.security = security

    def _run(
        self,
        severity: str,
        title: str,
        description: str,
        channel: Optional[str] = None,
        metadata: Optional[str] = None,
    ) -> str:
        """Send an alert.
        
        Args:
            severity: Alert severity (critical, high, medium, low, info)
            title: Alert title
            description: Alert description
            channel: Optional channel name
            metadata: Optional JSON string of metadata
            
        Returns:
            Result message
        """
        try:
            import json
            meta_dict = json.loads(metadata) if metadata else {}
            # Scrub metadata before sending
            scrubbed_meta = self.security.scrub_dict(meta_dict)
            # Scrub description
            scrubbed_desc = self.security.scrub(description)

            result = self.messenger_plugin.send_alert(
                severity=severity,
                title=title,
                description=scrubbed_desc,
                metadata=scrubbed_meta,
            )

            if channel:
                # Also send a regular message to the channel
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
        """Async version of send alert."""
        return self._run(severity, title, description, channel, metadata)


class Orchestrator:
    """Main orchestrator for SRE workflows using LangChain."""

    def __init__(
        self,
        plugin_loader: PluginLoader,
        security: SecurityMiddleware,
        llm_url: str = "http://ollama:11434",
        model_name: str = "llama3.1",
    ):
        """Initialize the orchestrator.
        
        Args:
            plugin_loader: PluginLoader instance with loaded plugins
            security: SecurityMiddleware for data scrubbing
            llm_url: URL of the local Ollama instance
            model_name: Name of the Ollama model to use
        """
        self.plugin_loader = plugin_loader
        self.security = security
        self.llm = ChatOllama(base_url=llm_url, model=model_name, temperature=0.1)

        # Build tools from plugins
        self.tools: List[BaseTool] = []
        self._build_tools()

        # Create agent
        self.agent = self._create_agent()

    def _build_tools(self):
        """Build LangChain tools from loaded plugins."""
        # Add metrics tool if available
        metrics_plugin = self.plugin_loader.get_metrics_plugin()
        if metrics_plugin:
            self.tools.append(MetricsTool(metrics_plugin, self.security))
            logger.info("Added metrics tool to agent")

        # Add knowledge tool if available
        knowledge_plugin = self.plugin_loader.get_knowledge_plugin()
        if knowledge_plugin:
            self.tools.append(KnowledgeTool(knowledge_plugin, self.security))
            logger.info("Added knowledge tool to agent")

        # Add messenger tool if available
        messenger_plugin = self.plugin_loader.get_messenger_plugin()
        if messenger_plugin:
            self.tools.append(MessengerTool(messenger_plugin, self.security))
            logger.info("Added messenger tool to agent")

        if not self.tools:
            logger.warning("No plugins loaded - agent will have no tools")

    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent executor.
        
        Returns:
            AgentExecutor instance
        """
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
        """Process an incident using the agent.
        
        Args:
            incident_title: Title of the incident
            incident_description: Description of the incident
            severity: Severity level
            
        Returns:
            Dictionary with processing results
        """
        # Scrub input before processing
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
            result = await self.agent.ainvoke({"input": query, "chat_history": []})
            return {
                "status": "processed",
                "response": result.get("output", ""),
                "scrubbed": True,
            }
        except Exception as e:
            logger.error(f"Error processing incident: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
            }

    async def query(self, user_query: str) -> Dict[str, Any]:
        """Process a general query using the agent.
        
        Args:
            user_query: User's query string
            
        Returns:
            Dictionary with query results
        """
        # Scrub input before processing
        scrubbed_query = self.security.scrub(user_query)

        try:
            result = await self.agent.ainvoke({"input": scrubbed_query, "chat_history": []})
            return {
                "status": "success",
                "response": result.get("output", ""),
                "scrubbed": True,
            }
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
            }
