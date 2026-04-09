"""Auto-discovers plugins from /plugins that implement BaseMetrics, BaseKnowledge, or BaseMessenger."""

import importlib
import inspect
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Type

from core.base import BaseKnowledge, BaseMessenger, BaseMetrics

logger = logging.getLogger(__name__)


class PluginLoader:

    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.metrics_plugins: Dict[str, BaseMetrics] = {}
        self.knowledge_plugins: Dict[str, BaseKnowledge] = {}
        self.messenger_plugins: Dict[str, BaseMessenger] = {}
        self._load_all_plugins()

    def _load_all_plugins(self):
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory '{self.plugins_dir}' does not exist")
            return

        for root, dirs, files in os.walk(self.plugins_dir):
            dirs[:] = [d for d in dirs if d != "__pycache__"]

            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    file_path = Path(root) / file
                    self._load_plugin_from_file(file_path)

    def _load_plugin_from_file(self, file_path: Path):
        try:
            project_root = self.plugins_dir.parent
            relative_path = file_path.relative_to(project_root)
            module_path = str(relative_path.with_suffix("")).replace(os.sep, ".")

            logger.debug(f"Loading plugin from: {module_path}")
            module = importlib.import_module(module_path)

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ != module_path:
                    continue

                if self._is_plugin_class(obj):
                    self._register_plugin(obj)

        except Exception as e:
            logger.error(
                f"Failed to load plugin from {file_path}: {str(e)}", exc_info=True
            )

    def _is_plugin_class(self, cls: Type) -> bool:
        bases = inspect.getmro(cls)
        return (
            BaseMetrics in bases or BaseKnowledge in bases or BaseMessenger in bases
        ) and cls not in (BaseMetrics, BaseKnowledge, BaseMessenger)

    def _register_plugin(self, plugin_class: Type):
        try:
            try:
                plugin_instance = plugin_class()
            except TypeError:
                logger.warning(
                    f"Plugin {plugin_class.__name__} requires initialization parameters. "
                    "Skipping automatic registration. Consider adding to config.yaml."
                )
                return

            if isinstance(plugin_instance, BaseMetrics):
                plugin_name = plugin_instance.name
                self.metrics_plugins[plugin_name] = plugin_instance
                logger.info(
                    f"Registered metrics plugin: {plugin_name} ({plugin_class.__name__})"
                )

            elif isinstance(plugin_instance, BaseKnowledge):
                plugin_name = plugin_instance.name
                self.knowledge_plugins[plugin_name] = plugin_instance
                logger.info(
                    f"Registered knowledge plugin: {plugin_name} ({plugin_class.__name__})"
                )

            elif isinstance(plugin_instance, BaseMessenger):
                plugin_name = plugin_instance.name
                self.messenger_plugins[plugin_name] = plugin_instance
                logger.info(
                    f"Registered messenger plugin: {plugin_name} ({plugin_class.__name__})"
                )

        except Exception as e:
            logger.error(
                f"Failed to register plugin {plugin_class.__name__}: {str(e)}",
                exc_info=True,
            )

    def get_metrics_plugin(self, name: Optional[str] = None) -> Optional[BaseMetrics]:
        if name:
            return self.metrics_plugins.get(name)
        elif self.metrics_plugins:
            return next(iter(self.metrics_plugins.values()))
        return None

    def get_knowledge_plugin(
        self, name: Optional[str] = None
    ) -> Optional[BaseKnowledge]:
        if name:
            return self.knowledge_plugins.get(name)
        elif self.knowledge_plugins:
            return next(iter(self.knowledge_plugins.values()))
        return None

    def get_messenger_plugin(
        self, name: Optional[str] = None
    ) -> Optional[BaseMessenger]:
        if name:
            return self.messenger_plugins.get(name)
        elif self.messenger_plugins:
            return next(iter(self.messenger_plugins.values()))
        return None

    def list_metrics_plugins(self) -> List[str]:
        return list(self.metrics_plugins.keys())

    def list_knowledge_plugins(self) -> List[str]:
        return list(self.knowledge_plugins.keys())

    def list_messenger_plugins(self) -> List[str]:
        return list(self.messenger_plugins.keys())
