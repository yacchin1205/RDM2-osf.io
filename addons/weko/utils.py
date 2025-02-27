import logging
import re

from osf.models.metaschema import RegistrationSchema


REGISTRATION_METADATA_MAPPING_PACKAGING_SIMPLE_ZIP = 'http://purl.org/net/sword/3.0/package/SimpleZip'
REGISTRATION_METADATA_MAPPING_PACKAGING_SWORD_BAGIT = 'http://purl.org/net/sword/3.0/package/SWORDBagIt'

logger = logging.getLogger(__name__)


def _validate_mapping_element(element):
    if isinstance(element, list):
        for e in element:
            if isinstance(e, str):
                continue
            _validate_mapping_element(e)
        return
    for key, v in element.items():
        if key.startswith('@'):
            if key not in ['@type', '@createIf']:
                raise ValueError(f'Unexpected special property: {key}')
            continue
        if not re.match(r'([\.a-zA-Z_]+)(\[[A-Z_]*\])?', key):
            raise ValueError(f'Unexpected key format "{key}" (must be [a-zA-Z_]+[[A-Z_]*]?)')
        if isinstance(v, str):
            continue
        _validate_mapping_element(v)


def _validate_metadata_element(element):
    if not isinstance(element, dict):
        raise ValueError('Metadata object must be dict')
    if len(element) == 0:
        raise ValueError('Metadata object cannot be empty')
    if 'packaging' not in element:
        raise ValueError('Metadata object must have packaging')
    packaging_type = element['packaging']
    if not isinstance(packaging_type, str):
        raise ValueError('Metadata packaging must be string')
    if packaging_type not in [
        REGISTRATION_METADATA_MAPPING_PACKAGING_SIMPLE_ZIP,
        REGISTRATION_METADATA_MAPPING_PACKAGING_SWORD_BAGIT,
    ]:
        raise ValueError(f'Unexpected packaging "{packaging_type}"')
    if 'itemtype' not in element and packaging_type == REGISTRATION_METADATA_MAPPING_PACKAGING_SIMPLE_ZIP:
        raise ValueError('Metadata object must have itemtype for SimpleZip packaging')
    for key, v in element.items():
        if key == 'itemtype':
            _validate_itemtype_element(v)
            continue
        if key in ['packaging']:
            continue
        raise ValueError(f'Unexpected key "{key}" in metadata')


def _validate_itemtype_element(element):
    if not isinstance(element, dict):
        raise ValueError('Itemtype object must be dict')
    if len(element) == 0:
        raise ValueError('Itemtype object cannot be empty')
    if 'name' not in element:
        raise ValueError('Itemtype object must have name')
    if 'schema' not in element:
        raise ValueError('Itemtype object must have schema')
    for key, v in element.items():
        if key in ['name', 'schema']:
            if not isinstance(v, str):
                raise ValueError(f'Itemtype "{key}" must be string')
            continue
        raise ValueError(f'Unexpected key "{key}" in itemtype')


def validate_mapping(mapping):
    if not isinstance(mapping, dict):
        raise ValueError('Mapping object must be dict')
    if len(mapping) == 0:
        raise ValueError('Mapping object cannot be empty')
    if '@metadata' not in mapping:
        raise ValueError('Mapping object must have @metadata')
    for key, element in mapping.items():
        if element is None:
            continue
        if key == '@metadata':
            _validate_metadata_element(element)
            continue
        if key != '_' and '@type' not in element:
            raise ValueError(f'Mapping "{key}" has no types')
        if key == '_' and '@type' in element:
            raise ValueError(f'Mapping "_" cannot have @type property')
        if key == '_' and '@createIf' in element:
            raise ValueError(f'Mapping "_" cannot have @createIf property')
        _validate_mapping_element(element)


def ensure_registration_metadata_mapping(schema_name, mapping):
    validate_mapping(mapping)
    packaging_type = mapping['@metadata']['packaging']

    from .models import RegistrationMetadataMapping
    registration_schema = RegistrationSchema.objects.filter(
        name=schema_name
    ).order_by('-schema_version').first()
    mapping_query = RegistrationMetadataMapping.objects.filter(
        registration_schema_id=registration_schema._id,
        packaging_type=packaging_type,
    )
    entity = None
    if mapping_query.exists():
        entity = mapping_query.first()
    elif packaging_type == REGISTRATION_METADATA_MAPPING_PACKAGING_SIMPLE_ZIP:
        # SimpleZip is default packaging type
        old_mapping_query = RegistrationMetadataMapping.objects.filter(
            registration_schema_id=registration_schema._id,
            packaging_type=None,
        )
        if old_mapping_query.exists():
            entity = old_mapping_query.first()
    if entity is None:
        entity = RegistrationMetadataMapping.objects.create(
            registration_schema_id=registration_schema._id,
            packaging_type=packaging_type,
        )
    entity.rules = mapping
    entity.packaging_type = packaging_type
    logger.info(f'Mapping registered: {registration_schema._id}, {packaging_type}, {mapping}')
    entity.save()
