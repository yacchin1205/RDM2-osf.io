import json
import logging
from jsonpath_ng.ext import parse

from django.core import serializers
from osf.models.metaschema import RegistrationSchema

from .settings import MAPPINGS


logger = logging.getLogger(__name__)


def _string_values_to_string(mapping_item, doc, context, values, in_json):
    if len(values) == 0:
        return None
    return values[0].value

def _jsonarray_values_to_string(mapping_item, doc, context, values, in_json):
    if 'template' in mapping_item:
        r = sum([
            [_convert_metadata_item(mapping_item['template'], ve, context, in_json=True) for ve in v.value]
            for v in values
        ], [])
    else:
        r = [v.value for v in values]
    if in_json:
        return r
    return json.dumps(r)

def _jsonobject_values_to_string(mapping_item, doc, context, values, in_json):
    if len(values) == 0:
        return None
    if 'template' in mapping_item:
        r = dict([
            (k, _convert_metadata_item(v, values[0].value, context, in_json=True))
            for k, v in mapping_item['template'].items()
        ])
    else:
        r = values[0].value
    if in_json:
        return r
    return json.dumps(r)

_values_to_string_types = {
    'string': _string_values_to_string,
    'jsonarray': _jsonarray_values_to_string,
    'jsonobject': _jsonobject_values_to_string,
}

def generate_file_metadata_items(node, file_node, base_metadata):
    r = []
    basedata = {}
    global_doc = _to_json_doc(node, file_node)
    logger.info(f'Global Document: {global_doc}')
    for mapping in MAPPINGS:
        schema = RegistrationSchema.objects.get_latest_version(mapping['schema'])
        if 'base' in mapping:
            base_schema = RegistrationSchema.objects.get_latest_version(mapping['base'])
            if base_metadata is None:
                continue
            bases = [item for item in base_metadata['items'] if item['schema'] == base_schema._id]
            if len(bases) == 0:
                continue
            base = bases[0]
            logger.info(f'Base: {base}')
        else:
            base = None
        doc = dict([(k, v) for k, v in global_doc.items()])
        doc.update({
            'base': dict([(k, v['value'] if 'value' in v else None) for k, v in base['data'].items()]) if base is not None else None,
        })
        logger.info(f'Document: {doc}')
        data = _generate_file_metadata_item(mapping, schema, doc)
        if schema._id in basedata:
            basedata[schema._id].update(data)
            continue
        basedata[schema._id] = data
        r.append({
            'schema': schema._id,
            'data': data,
        })
    return r

def _values_to_string(mapping_item, doc, context, values, in_json):
    type = mapping_item['type']
    return _values_to_string_types[type](mapping_item, doc, context, values, in_json)

def _convert_metadata_item(mapping_item, doc, context, in_json=False):
    logger.debug(f'convert metadata: {doc}')
    if 'jsonpath' not in mapping_item:
        return None
    contextdoc = dict([(k, v) for k, v in doc.items()])
    contextdoc.update({
        '$context': context
    })
    jsonpath_expr = parse(mapping_item['jsonpath'])
    values = jsonpath_expr.find(contextdoc)
    return _values_to_string(mapping_item, doc, context, values, in_json)

def _generate_file_metadata_item(mapping, schema, doc):
    r = {}
    for k, v in mapping['items'].items():
        item = _convert_metadata_item(v, doc, doc)
        if item is None:
            continue
        r[k] = {
            'comments': [],
            'extra': [],
            'value': item,
        }
    return r

def _to_json_doc(node, file_node):
    return {
        'node': _to_json_node(node),
        'file': _to_json_file(file_node),
    }

def _to_json_node(node):
    if node is None:
        return None
    r = _to_json_django_fields(node)
    r['contributors'] = [_to_json_contributor(node, u) for u in node.contributors.all()]
    r['affiliated_institutions'] = [_to_json_django_fields(i) for i in node.affiliated_institutions.all()]
    return r

def _to_json_contributor(node, user):
    r = _to_json_django_fields(user)
    if 'password' in r:
        del r['password']
    r['permissions'] = dict([(k, True) for k in node.get_permissions(user)])
    return r

def _to_json_file(file_node):
    if file_node is None:
        return None
    if isinstance(file_node, dict):
        return file_node['attributes']
    r = _to_json_django_fields(file_node)
    return r

def _to_json_django_fields(obj):
    return json.loads(serializers.serialize('json', [obj]))[0]['fields']