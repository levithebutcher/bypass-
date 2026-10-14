"""Plugin manager that discovers and auto-loads all bypasser plugins at startup."""

import os
import sys
import inspect
import importlib
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from bypassers.base import BaseBypasser
from bypassers.generic import GenericBypasser
from bypassers.exceptions import BypassError, SafetyBlockedError
from utils.safety import is_dangerous_url

logger = logging.getLogger(__name__)


class BypasserManager:
    """Discovers, loads, and dispatches bypasser plugins."""

    def __init__(self):
        self.plugins: List[BaseBypasser] = []
        self.generic_plugin: Optional[GenericBypasser] = None
        self._load_plugins()

    def _load_plugins(self) -> None:
        """Dynamically scans and imports all plugin files in the bypassers directory."""
        package_dir = Path(__file__).resolve().parent
        loaded_count = 0

        # Files to skip
        ignored_files = {"base.py", "manager.py", "exceptions.py", "__init__.py"}

        for item in sorted(package_dir.glob("*.py")):
            if item.name in ignored_files or item.name.startswith("_"):
                continue

            module_name = f"bypassers.{item.stem}"
            try:
                module = importlib.import_module(module_name)
                # Find all classes that inherit from BaseBypasser
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        inspect.isclass(attr)
                        and issubclass(attr, BaseBypasser)
                        and attr is not BaseBypasser
                    ):
                        instance = attr()
                        if isinstance(instance, GenericBypasser):
                            self.generic_plugin = instance
                        else:
                            self.plugins.append(instance)
                        loaded_count += 1
                        logger.debug("Loaded bypasser plugin: %s (%s)", instance.name, module_name)
            except Exception as e:
                logger.error("Failed to load plugin from %s: %s", item.name, e, exc_info=True)

        # Sort plugins by priority (highest first)
        self.plugins.sort(key=lambda p: getattr(p, "priority", 10), reverse=True)

        if not self.generic_plugin:
            self.generic_plugin = GenericBypasser()

        logger.info("Auto-loaded %d specialized bypasser plugins + Generic fallback solver.", len(self.plugins))

    def get_bypasser_for_url(self, url: str) -> BaseBypasser:
        """Finds the highest-priority plugin matching the given URL."""
        for plugin in self.plugins:
            try:
                if plugin.match(url):
                    return plugin
            except Exception:
                continue
        return self.generic_plugin

    async def bypass(self, url: str) -> Tuple[str, str]:
        """
        Executes link bypass using the best matched plugin.
        Falls back to GenericBypasser if the specialized plugin encounters an error.
        Returns: (final_url, bypasser_name)
        """
        # Security pre-check
        is_bad, bad_reason = is_dangerous_url(url)
        if is_bad:
            raise SafetyBlockedError(bad_reason)

        selected_plugin = self.get_bypasser_for_url(url)
        logger.info("Bypassing URL [%s] with plugin [%s]", url, selected_plugin.name)

        try:
            result = await selected_plugin.bypass(url)
            
            # Post-check resolved destination
            is_bad_dest, bad_dest_reason = is_dangerous_url(result)
            if is_bad_dest:
                raise SafetyBlockedError(bad_dest_reason)
                
            return result, selected_plugin.name
        except SafetyBlockedError:
            raise
        except Exception as primary_error:
            # If specialized plugin failed and it wasn't already generic, try generic fallback
            if selected_plugin is not self.generic_plugin:
                logger.warning(
                    "Specialized plugin [%s] failed on %s (%s). Attempting generic fallback...",
                    selected_plugin.name, url, primary_error
                )
                try:
                    fallback_result = await self.generic_plugin.bypass(url)
                    is_bad_dest, bad_dest_reason = is_dangerous_url(fallback_result)
                    if is_bad_dest:
                        raise SafetyBlockedError(bad_dest_reason)
                    return fallback_result, f"{selected_plugin.name} (Fallback)"
                except Exception as fallback_error:
                    logger.debug("Generic fallback also failed: %s", fallback_error)
            
            # Re-raise the primary error
            raise primary_error

    def get_supported_sites(self) -> List[Dict[str, Any]]:
        """Returns metadata for all loaded plugins for the /sites command."""
        sites = []
        for p in self.plugins:
            sites.append({
                "name": p.name,
                "domains": p.domains,
                "priority": getattr(p, "priority", 10),
            })
        return sites


# Global singleton instance
bypasser_manager = BypasserManager()
