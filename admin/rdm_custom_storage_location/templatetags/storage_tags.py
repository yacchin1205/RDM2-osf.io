"""Custom template tags for storage admin integration"""

from django import template
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from django.utils.safestring import mark_safe
import logging

from ..template_utils import render_storage_template
from ..plugin_loader import is_admin_integration_available

register = template.Library()
logger = logging.getLogger(__name__)


@register.simple_tag
def include_storage_modal(provider_short_name):
    """
    Include storage modal template, trying plugin first, then fallback
    
    Args:
        provider_short_name (str): Short name of the storage provider
        
    Returns:
        str: Rendered modal template content
    """
    try:
        # Try plugin template first
        if is_admin_integration_available(provider_short_name):
            try:
                content = render_storage_template(
                    provider_name=provider_short_name,
                    template_type='modal',
                    context={},
                    fallback_template=None
                )
                if content:
                    logger.info(f"Using plugin template for {provider_short_name}")
                    return mark_safe(content)
            except Exception as e:
                logger.warning(f"Plugin template failed for {provider_short_name}: {e}")
        
        # Fall back to built-in template
        fallback_template = f'rdm_custom_storage_location/providers/{provider_short_name}_modal.html'
        try:
            content = render_to_string(fallback_template, {})
            logger.info(f"Using fallback template for {provider_short_name}")
            return mark_safe(content)
        except TemplateDoesNotExist:
            logger.error(f"No template found for {provider_short_name}")
            return mark_safe(f'<!-- No modal template available for {provider_short_name} -->')
    
    except Exception as e:
        logger.error(f"Error including storage modal for {provider_short_name}: {e}")
        return mark_safe(f'<!-- Error loading modal for {provider_short_name}: {e} -->')


@register.simple_tag
def get_storage_modal_content(provider_short_name, context=None):
    """
    Get storage modal content without rendering
    
    Args:
        provider_short_name (str): Short name of the storage provider
        context (dict): Template context variables
        
    Returns:
        str: Modal template content
    """
    if context is None:
        context = {}
    
    return render_storage_template(
        provider_name=provider_short_name,
        template_type='modal',
        context=context
    )


@register.filter
def is_plugin_available(provider_short_name):
    """
    Check if a storage provider has plugin template available
    
    Args:
        provider_short_name (str): Short name of the storage provider
        
    Returns:
        bool: True if plugin is available
    """
    return is_admin_integration_available(provider_short_name)