"""Plugin loader for storage admin integrations

This module discovers and loads admin integration functions from external storage packages.
"""

import importlib
import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class StorageAdminPluginLoader:
    """Manages loading and registration of storage admin integration plugins"""
    
    def __init__(self):
        self.loaded_integrations: Dict[str, Dict[str, Any]] = {}
        self.failed_integrations: list = []
    
    def discover_integrations(self) -> Dict[str, Dict[str, Any]]:
        """
        Discover available storage admin integrations using entry points
        
        Returns:
            Dictionary of discovered integration configurations
        """
        discovered = {}
        
        try:
            # Try to use importlib.metadata (Python 3.8+)
            from importlib.metadata import entry_points
            
            eps = entry_points()
            if hasattr(eps, 'select'):
                # Python 3.10+ style
                admin_integrations = eps.select(group='rdm.admin_integrations')
            else:
                # Python 3.8-3.9 style
                admin_integrations = eps.get('rdm.admin_integrations', [])
                
            for entry_point in admin_integrations:
                try:
                    integration_func = entry_point.load()
                    integration_info = integration_func()
                    discovered[entry_point.name] = integration_info
                    logger.info(f"Discovered admin integration: {entry_point.name}")
                except Exception as e:
                    logger.warning(f"Failed to load admin integration {entry_point.name}: {e}")
                    self.failed_integrations.append(entry_point.name)
                    
        except ImportError:
            # Fallback to pkg_resources for older Python versions
            try:
                import pkg_resources
                for entry_point in pkg_resources.iter_entry_points('rdm.admin_integrations'):
                    try:
                        integration_func = entry_point.load()
                        integration_info = integration_func()
                        discovered[entry_point.name] = integration_info
                        logger.info(f"Discovered admin integration: {entry_point.name}")
                    except Exception as e:
                        logger.warning(f"Failed to load admin integration {entry_point.name}: {e}")
                        self.failed_integrations.append(entry_point.name)
            except ImportError:
                logger.warning("No entry point discovery mechanism available")
        
        return discovered
    
    def load_integration(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific admin integration
        
        Args:
            provider_name: Name of the storage provider
            
        Returns:
            Integration info dictionary or None if failed
        """
        # Check if already loaded
        if provider_name in self.loaded_integrations:
            return self.loaded_integrations[provider_name]
        
        # Try to discover and load
        discovered = self.discover_integrations()
        if provider_name in discovered:
            integration_info = discovered[provider_name]
            self.loaded_integrations[provider_name] = integration_info
            return integration_info
        
        return None
    
    def get_test_connection_func(self, provider_name: str) -> Optional[Callable]:
        """
        Get connection test function for a specific provider
        
        Args:
            provider_name: Name of the storage provider
            
        Returns:
            Test connection function or None if not available
        """
        integration_info = self.load_integration(provider_name)
        if integration_info:
            return integration_info.get('test_connection_func')
        return None
    
    def get_template_content(self, provider_name: str, template_name: str) -> Optional[str]:
        """
        Get template content for a specific provider
        
        Args:
            provider_name: Name of the storage provider
            template_name: Name of the template
            
        Returns:
            Template content as string or None if not available
        """
        integration_info = self.load_integration(provider_name)
        if integration_info and 'template_functions' in integration_info:
            get_content_func = integration_info['template_functions'].get('get_template_content')
            if get_content_func:
                try:
                    return get_content_func(template_name)
                except Exception as e:
                    logger.error(f"Failed to get template content for {provider_name}: {e}")
        return None
    
    def get_template_path(self, provider_name: str, template_name: str) -> Optional[str]:
        """
        Get template path for a specific provider
        
        Args:
            provider_name: Name of the storage provider
            template_name: Name of the template
            
        Returns:
            Template path or None if not available
        """
        integration_info = self.load_integration(provider_name)
        if integration_info and 'template_functions' in integration_info:
            get_path_func = integration_info['template_functions'].get('get_template_path')
            if get_path_func:
                try:
                    return get_path_func(template_name)
                except Exception as e:
                    logger.error(f"Failed to get template path for {provider_name}: {e}")
        return None
    
    def get_available_templates(self, provider_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Get available templates for a specific provider
        
        Args:
            provider_name: Name of the storage provider
            
        Returns:
            Dictionary of available templates
        """
        integration_info = self.load_integration(provider_name)
        if integration_info and 'templates' in integration_info:
            return integration_info['templates']
        return {}
    
    def get_all_integrations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available admin integrations
        
        Returns:
            Dictionary of all loaded integrations
        """
        # Load any newly discovered integrations
        discovered = self.discover_integrations()
        for name, info in discovered.items():
            if name not in self.loaded_integrations:
                self.loaded_integrations[name] = info
        
        return self.loaded_integrations.copy()
    
    def is_integration_available(self, provider_name: str) -> bool:
        """Check if admin integration is available for a provider"""
        return (provider_name in self.loaded_integrations or 
                provider_name in self.discover_integrations())


# Global loader instance
plugin_loader = StorageAdminPluginLoader()


def get_test_connection_function(provider_name: str) -> Optional[Callable]:
    """
    Get test connection function for a storage provider
    
    Args:
        provider_name: Name of the storage provider
        
    Returns:
        Test connection function or None if not available
    """
    return plugin_loader.get_test_connection_func(provider_name)


def is_admin_integration_available(provider_name: str) -> bool:
    """Check if admin integration is available for a provider"""
    return plugin_loader.is_integration_available(provider_name)


def get_all_admin_integrations() -> Dict[str, Dict[str, Any]]:
    """Get all available admin integrations"""
    return plugin_loader.get_all_integrations()


def get_admin_integration_status() -> Dict[str, Any]:
    """Get status of admin integration loading"""
    return {
        'loaded': list(plugin_loader.loaded_integrations.keys()),
        'failed': plugin_loader.failed_integrations.copy(),
        'total_discovered': len(plugin_loader.loaded_integrations) + len(plugin_loader.failed_integrations)
    }


def get_plugin_template_content(provider_name: str, template_name: str) -> Optional[str]:
    """
    Get template content from storage plugin
    
    Args:
        provider_name: Name of the storage provider
        template_name: Name of the template
        
    Returns:
        Template content as string or None if not available
    """
    return plugin_loader.get_template_content(provider_name, template_name)


def get_plugin_template_path(provider_name: str, template_name: str) -> Optional[str]:
    """
    Get template path from storage plugin
    
    Args:
        provider_name: Name of the storage provider
        template_name: Name of the template
        
    Returns:
        Template path or None if not available
    """
    return plugin_loader.get_template_path(provider_name, template_name)


def get_available_plugin_templates(provider_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Get available templates for a storage provider
    
    Args:
        provider_name: Name of the storage provider
        
    Returns:
        Dictionary of available templates
    """
    return plugin_loader.get_available_templates(provider_name)