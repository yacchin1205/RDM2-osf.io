"""Template utilities for storage admin integration

This module provides utilities for working with both built-in and plugin templates
in the storage admin interface.
"""

import os
import logging
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from django.http import HttpResponse

from .template_loader import (
    render_plugin_template, 
    check_plugin_template_availability,
    get_plugin_template_choices
)
from .plugin_loader import is_admin_integration_available

logger = logging.getLogger(__name__)


def render_storage_template(provider_name, template_type, context=None, fallback_template=None):
    """
    Render a storage-specific template, trying plugin first, then fallback
    
    Args:
        provider_name (str): Name of the storage provider (e.g., 's3compat')
        template_type (str): Type of template (e.g., 'modal')
        context (dict): Template context variables
        fallback_template (str): Fallback template path if plugin not available
        
    Returns:
        str: Rendered template content
        
    Raises:
        TemplateDoesNotExist: If neither plugin nor fallback template found
    """
    if context is None:
        context = {}
    
    # Template name mapping
    template_mapping = {
        'modal': f'{provider_name}_modal.html'
    }
    
    template_name = template_mapping.get(template_type, f'{provider_name}_{template_type}.html')
    
    # Try plugin template first
    if is_admin_integration_available(provider_name):
        try:
            if check_plugin_template_availability(provider_name, template_name):
                logger.info(f"Using plugin template for {provider_name}: {template_name}")
                return render_plugin_template(provider_name, template_name, context)
        except Exception as e:
            logger.warning(f"Failed to render plugin template {provider_name}:{template_name}: {e}")
    
    # Fall back to built-in template
    if fallback_template:
        try:
            logger.info(f"Using fallback template for {provider_name}: {fallback_template}")
            return render_to_string(fallback_template, context)
        except TemplateDoesNotExist:
            logger.error(f"Fallback template not found: {fallback_template}")
    
    # If all else fails, create a basic error template
    error_message = f"Template not available for {provider_name}"
    return f'<div class="alert alert-warning">{error_message}</div>'


def get_storage_modal_template(provider_name, context=None):
    """
    Get modal template for a specific storage provider
    
    Args:
        provider_name (str): Name of the storage provider
        context (dict): Template context variables
        
    Returns:
        str: Rendered modal template content
    """
    fallback_template = f'rdm_custom_storage_location/providers/{provider_name}_modal.html'
    
    return render_storage_template(
        provider_name=provider_name,
        template_type='modal',
        context=context,
        fallback_template=fallback_template
    )


def render_storage_template_response(provider_name, template_type, context=None, content_type='text/html'):
    """
    Render storage template and return HttpResponse
    
    Args:
        provider_name (str): Name of the storage provider
        template_type (str): Type of template
        context (dict): Template context variables
        content_type (str): HTTP content type
        
    Returns:
        HttpResponse: Response with rendered template
    """
    try:
        content = render_storage_template(provider_name, template_type, context)
        return HttpResponse(content, content_type=content_type)
    except Exception as e:
        logger.error(f"Failed to render storage template: {e}")
        error_content = f'<div class="alert alert-danger">Template error: {str(e)}</div>'
        return HttpResponse(error_content, content_type=content_type, status=500)


def list_available_storage_templates():
    """
    List all available storage templates (both plugin and built-in)
    
    Returns:
        dict: Available templates organized by provider
    """
    result = {
        'plugin_templates': get_plugin_template_choices(),
        'built_in_templates': _get_builtin_template_choices()
    }
    
    return result


def _get_builtin_template_choices():
    """
    Get available built-in templates
    
    Returns:
        dict: Built-in template information
    """
    # This would scan the admin/templates directory for built-in templates
    # For now, return known templates
    return {
        's3compatinstitutions': {
            'display_name': 'S3 Compatible Storage for Institutions',
            'templates': {
                'modal': 'rdm_custom_storage_location/providers/s3compatinstitutions_modal.html'
            }
        },
        's3compatb3': {
            'display_name': 'S3 Compatible Storage (Boto3)',
            'templates': {
                'modal': 'rdm_custom_storage_location/providers/s3compatb3_modal.html'
            }
        }
    }


def validate_storage_template(provider_name, template_type):
    """
    Validate that a storage template is available
    
    Args:
        provider_name (str): Name of the storage provider
        template_type (str): Type of template
        
    Returns:
        dict: Validation result with availability and source information
    """
    template_mapping = {
        'modal': f'{provider_name}_modal.html'
    }
    
    template_name = template_mapping.get(template_type, f'{provider_name}_{template_type}.html')
    
    result = {
        'provider_name': provider_name,
        'template_type': template_type,
        'template_name': template_name,
        'plugin_available': False,
        'fallback_available': False,
        'recommended_source': None
    }
    
    # Check plugin availability
    if is_admin_integration_available(provider_name):
        result['plugin_available'] = check_plugin_template_availability(provider_name, template_name)
    
    # Check fallback availability
    fallback_template = f'rdm_custom_storage_location/providers/{provider_name}_modal.html'
    try:
        render_to_string(fallback_template, {})
        result['fallback_available'] = True
    except TemplateDoesNotExist:
        result['fallback_available'] = False
    
    # Determine recommended source
    if result['plugin_available']:
        result['recommended_source'] = 'plugin'
    elif result['fallback_available']:
        result['recommended_source'] = 'fallback'
    else:
        result['recommended_source'] = None
    
    return result