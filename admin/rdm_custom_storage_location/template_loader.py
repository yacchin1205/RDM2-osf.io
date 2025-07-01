"""Plugin template loader for Django

This module provides a custom Django template loader that can load templates
from external storage plugins dynamically.
"""

import logging
from django.template import TemplateDoesNotExist
from django.template.loaders.base import Loader as BaseLoader
from django.template.backends.django import DjangoTemplates
from django.template import Template

from .plugin_loader import get_plugin_template_content, get_all_admin_integrations

logger = logging.getLogger(__name__)


class PluginTemplateLoader(BaseLoader):
    """
    Django template loader that loads templates from storage plugins
    
    This loader checks for templates in external storage packages when
    the standard template loaders fail to find a template.
    """
    
    def __init__(self, engine, dirs=None):
        super().__init__(engine)
        self.dirs = dirs
        self._template_cache = {}
    
    def get_template_sources(self, template_name):
        """
        Generate possible template sources for plugin templates
        
        Args:
            template_name (str): Name of the template to find
            
        Yields:
            Template origins for plugin templates
        """
        # Check if this looks like a plugin template
        if self._is_plugin_template(template_name):
            provider_name = self._extract_provider_name(template_name)
            if provider_name:
                yield PluginTemplateOrigin(
                    name=template_name,
                    provider_name=provider_name,
                    loader=self
                )
    
    def get_contents(self, origin):
        """
        Get template contents from plugin
        
        Args:
            origin: Template origin object
            
        Returns:
            Template content as string
            
        Raises:
            TemplateDoesNotExist: If template cannot be found
        """
        if isinstance(origin, PluginTemplateOrigin):
            # Extract template name for plugin lookup
            template_file = origin.name.split('/')[-1]  # Get filename
            
            content = get_plugin_template_content(origin.provider_name, template_file)
            if content is not None:
                return content
        
        raise TemplateDoesNotExist(origin.name)
    
    def _is_plugin_template(self, template_name):
        """
        Check if template name indicates a plugin template
        
        Args:
            template_name (str): Template name to check
            
        Returns:
            bool: True if this could be a plugin template
        """
        # Check if template path contains provider-specific patterns
        plugin_patterns = [
            's3compat_modal.html',
            'rdm_custom_storage_location/providers/'
        ]
        
        return any(pattern in template_name for pattern in plugin_patterns)
    
    def _extract_provider_name(self, template_name):
        """
        Extract provider name from template path
        
        Args:
            template_name (str): Template name/path
            
        Returns:
            str: Provider name or None
        """
        # Map template patterns to provider names
        provider_mappings = {
            's3compat_modal.html': 's3compat',
            's3compat': 's3compat',
        }
        
        for pattern, provider in provider_mappings.items():
            if pattern in template_name:
                return provider
        
        return None


class PluginTemplateOrigin:
    """
    Template origin for plugin-based templates
    """
    
    def __init__(self, name, provider_name, loader):
        self.name = name
        self.provider_name = provider_name
        self.loader = loader
    
    def __str__(self):
        return f"plugin:{self.provider_name}:{self.name}"


def render_plugin_template(provider_name, template_name, context=None):
    """
    Render a template from a storage plugin
    
    Args:
        provider_name (str): Name of the storage provider
        template_name (str): Name of the template
        context (dict): Template context variables
        
    Returns:
        str: Rendered template content
        
    Raises:
        TemplateDoesNotExist: If template cannot be found
    """
    content = get_plugin_template_content(provider_name, template_name)
    if content is None:
        raise TemplateDoesNotExist(f"Plugin template not found: {provider_name}:{template_name}")
    
    # Create Django template from content
    template = Template(content)
    
    # Render with context
    from django.template import Context
    if context is None:
        context = {}
    
    django_context = Context(context)
    return template.render(django_context)


def get_plugin_template_choices():
    """
    Get available plugin templates for admin interface
    
    Returns:
        dict: Available templates organized by provider
    """
    integrations = get_all_admin_integrations()
    template_choices = {}
    
    for provider_name, integration_info in integrations.items():
        if 'templates' in integration_info:
            template_choices[provider_name] = {
                'display_name': integration_info.get('display_name', provider_name),
                'templates': integration_info['templates']
            }
    
    return template_choices


def check_plugin_template_availability(provider_name, template_name):
    """
    Check if a plugin template is available
    
    Args:
        provider_name (str): Name of the storage provider
        template_name (str): Name of the template
        
    Returns:
        bool: True if template is available
    """
    content = get_plugin_template_content(provider_name, template_name)
    return content is not None