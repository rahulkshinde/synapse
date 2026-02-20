"""Automatic plugin discovery and loading system.

This module implements a PluginLoader that automatically discovers and registers
any class in the /plugins directory that implements the base interfaces defined
in core.base. Plugins are loaded dynamically without requiring manual registration.
"""

import importlib
import inspect
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Type

from core.base import BaseKnowledge, BaseMessenger, BaseMetrics

logger = logging.getLogger(__name__)


class PluginLoader:
    """Automatic plugin discovery and registration system.
    
    Scans the /plugins directory for Python files and automatically loads
    any class that implements BaseMetrics, BaseKnowledge, or BaseMessenger.
    """

    def __init__(self, plugins_dir: str = "plugins"):
        """Initialize the plugin loader.
        
        Args:
            plugins_dir: Directory path to scan for plugins (default: "plugins")
        """
        self.plugins_dir = Path(plugins_dir)
        self.metrics_plugins: Dict[str, BaseMetrics] = {}
        self.knowledge_plugins: Dict[str, BaseKnowledge] = {}
        self.messenger_plugins: Dict[str, BaseMessenger] = {}
        self._load_all_plugins()

    def _load_all_plugins(self):
        """Discover and load all plugins from the plugins directory."""
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory '{self.plugins_dir}' does not exist")
            return

        # Walk through all subdirectories
        for root, dirs, files in os.walk(self.plugins_dir):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != "__pycache__"]

            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    file_path = Path(root) / file
                    self._load_plugin_from_file(file_path)

    def _load_plugin_from_file(self, file_path: Path):
        """Load plugins from a single Python file.
        
        Args:
            file_path: Path to the Python file to load
        """
        try:
            # Convert file path to module path
            # e.g., plugins/metrics/prometheus.py -> plugins.metrics.prometheus
            # Get the path relative to the project root (plugins_dir.parent)
            project_root = self.plugins_dir.parent
            relative_path = file_path.relative_to(project_root)
            module_path = str(relative_path.with_suffix("")).replace(os.sep, ".")

            logger.debug(f"Loading plugin from: {module_path}")

            # Import the module
            module = importlib.import_module(module_path)

            # Find all classes in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Skip if it's imported from elsewhere or is a base class
                if obj.__module__ != module_path:
                    continue

                # Check if it implements one of our base classes
                if self._is_plugin_class(obj):
                    self._register_plugin(obj)

        except Exception as e:
            logger.error(f"Failed to load plugin from {file_path}: {str(e)}", exc_info=True)

    def _is_plugin_class(self, cls: Type) -> bool:
        """Check if a class implements one of the base plugin interfaces.
        
        Args:
            cls: Class to check
            
        Returns:
            True if the class implements a base interface, False otherwise
        """
        # Get all base classes (including ABCs)
        bases = inspect.getmro(cls)

        # Check if it implements any of our base classes
        return (
            BaseMetrics in bases
            or BaseKnowledge in bases
            or BaseMessenger in bases
        ) and cls not in (BaseMetrics, BaseKnowledge, BaseMessenger)

    def _register_plugin(self, plugin_class: Type):
        """Register a plugin instance.
        
        Args:
            plugin_class: Plugin class to instantiate and register
        """
        try:
            # Try to instantiate the plugin
            # Some plugins may require initialization parameters
            # For now, try with no args, then with common config patterns
            try:
                plugin_instance = plugin_class()
            except TypeError:
                # Plugin requires initialization parameters
                # Try to get config from environment or use defaults
                logger.warning(
                    f"Plugin {plugin_class.__name__} requires initialization parameters. "
                    "Skipping automatic registration. Consider adding to config.yaml."
                )
                return

            # Determine plugin type and register
            if isinstance(plugin_instance, BaseMetrics):
                plugin_name = plugin_instance.name
                self.metrics_plugins[plugin_name] = plugin_instance
                logger.info(f"Registered metrics plugin: {plugin_name} ({plugin_class.__name__})")

            elif isinstance(plugin_instance, BaseKnowledge):
                plugin_name = plugin_instance.name
                self.knowledge_plugins[plugin_name] = plugin_instance
                logger.info(f"Registered knowledge plugin: {plugin_name} ({plugin_class.__name__})")

            elif isinstance(plugin_instance, BaseMessenger):
                plugin_name = plugin_instance.name
                self.messenger_plugins[plugin_name] = plugin_instance
                logger.info(f"Registered messenger plugin: {plugin_name} ({plugin_class.__name__})")

        except Exception as e:
            logger.error(f"Failed to register plugin {plugin_class.__name__}: {str(e)}", exc_info=True)

    def get_metrics_plugin(self, name: Optional[str] = None) -> Optional[BaseMetrics]:
        """Get a metrics plugin by name, or return the first available.
        
        Args:
            name: Optional plugin name. If None, returns the first available plugin.
            
        Returns:
            BaseMetrics instance or None if not found
        """
        if name:
            return self.metrics_plugins.get(name)
        elif self.metrics_plugins:
            return next(iter(self.metrics_plugins.values()))
        return None

    def get_knowledge_plugin(self, name: Optional[str] = None) -> Optional[BaseKnowledge]:
        """Get a knowledge plugin by name, or return the first available.
        
        Args:
            name: Optional plugin name. If None, returns the first available plugin.
            
        Returns:
            BaseKnowledge instance or None if not found
        """
        if name:
            return self.knowledge_plugins.get(name)
        elif self.knowledge_plugins:
            return next(iter(self.knowledge_plugins.values()))
        return None

    def get_messenger_plugin(self, name: Optional[str] = None) -> Optional[BaseMessenger]:
        """Get a messenger plugin by name, or return the first available.
        
        Args:
            name: Optional plugin name. If None, returns the first available plugin.
            
        Returns:
            BaseMessenger instance or None if not found
        """
        if name:
            return self.messenger_plugins.get(name)
        elif self.messenger_plugins:
            return next(iter(self.messenger_plugins.values()))
        return None

    def list_metrics_plugins(self) -> List[str]:
        """List all loaded metrics plugin names.
        
        Returns:
            List of plugin names
        """
        return list(self.metrics_plugins.keys())

    def list_knowledge_plugins(self) -> List[str]:
        """List all loaded knowledge plugin names.
        
        Returns:
            List of plugin names
        """
        return list(self.knowledge_plugins.keys())

    def list_messenger_plugins(self) -> List[str]:
        """List all loaded messenger plugin names.
        
        Returns:
            List of plugin names
        """
        return list(self.messenger_plugins.keys())
