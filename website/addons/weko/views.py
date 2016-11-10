"""Views for the node settings page."""
# -*- coding: utf-8 -*-
import datetime
import httplib as http
import uuid
import os
import zipfile
import tempfile
import re
from requests.exceptions import SSLError
from lxml import etree

from flask import request
from flask import redirect
from modularodm import Q
from modularodm.storage.base import KeyExistsException

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from website.addons.base import generic_views
from website.addons.weko import client
from website.addons.weko.model import WEKOProvider
from website.addons.weko.serializer import WEKOSerializer
from website.addons.weko import settings as weko_settings
from website.oauth.models import ExternalAccount
from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
    must_be_contributor_or_public
)
from website.util import rubeus, api_url_for
from website.util.sanitize import assert_clean
from website.oauth.utils import get_service
from website.oauth.signals import oauth_complete

SHORT_NAME = 'weko'
FULL_NAME = 'WEKO'

@must_be_logged_in
def weko_oauth_connect(repoid, auth):
    service = get_service(SHORT_NAME)
    return redirect(service.get_repo_auth_url(repoid))

@must_be_logged_in
def weko_oauth_callback(repoid, auth):
    user = auth.user
    provider = get_service(SHORT_NAME)

    # Retrieve permanent credentials from provider
    if not provider.repo_auth_callback(user=user, repoid=repoid):
        return {}

    if provider.account not in user.external_accounts:
        user.external_accounts.append(provider.account)
        user.save()

    oauth_complete.send(provider, account=provider.account, user=user)

    return {}


weko_account_list = generic_views.account_list(
    SHORT_NAME,
    WEKOSerializer
)

weko_import_auth = generic_views.import_auth(
    SHORT_NAME,
    WEKOSerializer
)

weko_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

weko_get_config = generic_views.get_config(
    SHORT_NAME,
    WEKOSerializer
)

## Auth ##

@must_be_logged_in
def weko_user_config_get(auth, **kwargs):
    """View for getting a JSON representation of the logged-in user's
    Dataverse user settings.
    """

    user_addon = auth.user.get_addon('weko')
    user_has_auth = False
    if user_addon:
        user_has_auth = user_addon.has_auth

    return {
        'result': {
            'userHasAuth': user_has_auth,
            'urls': {
                'create': api_url_for('weko_add_user_account'),
                'accounts': api_url_for('weko_account_list'),
            },
            'repositories': weko_settings.REPOSITORY_IDS
        },
    }, http.OK


## Config ##

@must_be_logged_in
def weko_add_user_account(auth, **kwargs):
    """Verifies new external account credentials and adds to user's list"""
    user = auth.user
    provider = WEKOProvider()

    host = request.json.get('host').rstrip('/')
    api_token = request.json.get('api_token')

    # Verify that credentials are valid
    client.connect_or_error(host, api_token)

    # Note: `DataverseSerializer` expects display_name to be a URL
    try:
        provider.account = ExternalAccount(
            provider=provider.short_name,
            provider_name=provider.name,
            display_name=host,       # no username; show host
            oauth_key=host,          # hijacked; now host
            oauth_secret=api_token,  # hijacked; now api_token
            provider_id=api_token,   # Change to username if Dataverse allows
        )
        provider.account.save()
    except KeyExistsException:
        # ... or get the old one
        provider.account = ExternalAccount.find_one(
            Q('provider', 'eq', provider.short_name) &
            Q('provider_id', 'eq', api_token)
        )

    if provider.account not in user.external_accounts:
        user.external_accounts.append(provider.account)

    user_addon = auth.user.get_addon('weko')
    if not user_addon:
        user.add_addon('weko')
    user.save()

    # Need to ensure that the user has dataverse enabled at this point
    user.get_or_add_addon('weko', auth=auth)
    user.save()

    return {}

@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def weko_set_config(node_addon, auth, **kwargs):
    """Saves selected WEKO and Index to node settings"""

    user_settings = node_addon.user_settings
    user = auth.user

    if user_settings and user_settings.owner != user:
        raise HTTPError(http.FORBIDDEN)

    try:
        assert_clean(request.json)
    except AssertionError:
        # TODO: Test me!
        raise HTTPError(http.NOT_ACCEPTABLE)

    index_id = request.json.get('index', {}).get('id')

    if index_id is None:
        return HTTPError(http.BAD_REQUEST)

    connection = client.connect_from_settings(weko_settings, node_addon)
    index = client.get_index_by_id(connection, index_id)

    node_addon.set_folder(index, auth)

    return {'index': index.title}, http.OK

## Crud ##

@must_be_contributor_or_public
@must_have_addon(SHORT_NAME, 'node')
def weko_get_serviceitemtype(node_addon, **kwargs):
    connection = client.connect_from_settings_or_401(weko_settings, node_addon)
    return client.get_serviceitemtype(connection)

@must_be_contributor_or_public
@must_have_addon(SHORT_NAME, 'node')
def weko_get_item_view(itemid, node_addon, **kwargs):
    weko_host = weko_settings.REPOSITORIES[node_addon.external_account.provider_id.split('@')[-1]]['host']
    connection = client.connect_from_settings_or_401(weko_settings, node_addon)
    index_url = client.get_all_indices(connection)[0].about
    base_url = re.compile(r'^(.+)\?action=.*$').match(index_url).group(1)
    return {'url': '{}?action=repository_uri&item_id={}'.format(base_url, itemid)}, http.OK

@must_have_permission('write')
@must_not_be_registration
@must_have_addon(SHORT_NAME, 'node')
def weko_create_index(node_addon, auth, **kwargs):
    node = node_addon.owner

    now = datetime.datetime.utcnow()
    parent_path = request.json.get('parent_path', None)
    title_ja = request.json.get('title_ja', None)
    title_en = request.json.get('title_en', None)

    connection = client.connect_from_settings_or_401(weko_settings, node_addon)
    if parent_path is None:
        parent_index_id = node_addon.index_id
    else:
        parent_index_id = parent_path.split('/') [-2]

    index_id = client.create_index(connection, title_ja, title_en,
                                   parent_index_id)

    # Add a log
    node.add_log(
        action='weko_index_created',
        params={
            'project': node.parent_id,
            'node': node._id,
            'filename': title_ja
        },
        auth=auth,
        log_date=now,
    )

    indices = client.get_all_indices(connection)

    return {'nodeId': node._id,
            'name': title_ja,
            'kind': 'folder',
            'path': _get_path(indices, index_id),
            'provider': SHORT_NAME}, http.OK

@must_have_permission('write')
@must_not_be_registration
@must_have_addon(SHORT_NAME, 'node')
def weko_upload_draft(node_addon, auth, **kwargs):
    node = node_addon.owner

    base_id = node._id + '-' + uuid.uuid1().hex
    fn = os.path.join(weko_settings.DRAFT_DIR,
                      'weko-' + base_id + '.draft')
    with open(fn, 'wb') as f:
        f.write(request.data)

    hasImportXml = False
    try:
        with zipfile.ZipFile(fn, 'r') as zf:
            hasImportXml = 'import.xml' in zf.namelist()
    except:
        pass
    return {'draft_id': base_id,
            'hasImportXml': hasImportXml,
            'nodeApiUrl': '/api/v1/project/{}/'.format(node._id)}, http.OK

@must_have_permission('write')
@must_not_be_registration
@must_have_addon(SHORT_NAME, 'node')
def weko_submit_draft(draftid, node_addon, auth, **kwargs):
    as_weko_export = request.json.get('asWEKOExport', False)
    target_index_id = request.json.get('insertIndex', None)
    target_index_id = target_index_id.split('/')[-2] if target_index_id is not None else node_addon.index_id

    connection = client.connect_from_settings_or_401(weko_settings, node_addon)
    uploaded_filename = request.json.get('filename', None)

    if as_weko_export:
        archived_file = os.path.join(weko_settings.DRAFT_DIR,
                                     'weko-' + draftid + '.draft')
    else:
        service_item_type = int(request.json.get('serviceItemType', None))
        item_types = client.get_serviceitemtype(connection)['item_type']
        internal_item_type_id = 10000 + service_item_type + 1

        item_type = item_types[service_item_type]
        title, ext = os.path.splitext(uploaded_filename)
        title_en = title

        contributors = []
        for contributor in node_addon.owner.contributors:
            contributors.append({'family': contributor.family_name,
                                 'name': contributor.given_name})

        with tempfile.NamedTemporaryFile(delete=False) as ziptf:
            with zipfile.ZipFile(ziptf, 'w', zipfile.ZIP_DEFLATED) as zipf:
                with tempfile.NamedTemporaryFile(delete=False) as importf:
                    post_xml = client.create_import_xml(item_type,
                                                        internal_item_type_id,
                                                        uploaded_filename,
                                                        title, title_en,
                                                        contributors)
                    importf.write(etree.tostring(post_xml,
                                                 encoding='UTF-8',
                                                 xml_declaration=True))
                    importfn = importf.name
                zipf.write(importfn, 'import.xml')
                zipf.write(os.path.join(weko_settings.DRAFT_DIR,
                                     'weko-' + draftid + '.draft'),
                           uploaded_filename)
            archived_file = ziptf.name

    with open(archived_file, 'r') as f:
        client.post(connection, target_index_id, f,
                    os.path.getsize(archived_file))

    return {'draft_id': draftid, 'status': 'submitted'}, http.OK

@must_have_permission('write')
@must_not_be_registration
@must_have_addon(SHORT_NAME, 'node')
def weko_cancel_draft(draftid, node_addon, auth, **kwargs):
    os.remove(os.path.join(weko_settings.DRAFT_DIR,
                           'weko-' + draftid + '.draft'))
    return {'draft_id': draftid, 'status': 'canceled'}, http.OK

## HGRID ##

def _weko_root_folder(node_addon, auth, **kwargs):
    node = node_addon.owner

    # Quit if no indices linked
    if not node_addon.complete:
        return []

    connection = client.connect_from_settings(weko_settings, node_addon)
    index = client.get_index_by_id(connection, node_addon.index_id)

    if index is None:
        return []

    return [rubeus.build_addon_root(
        node_addon,
        node_addon.index_title,
        permissions={'view': True, 'edit': True},
        private_key=kwargs.get('view_only', None),
    )]


@must_be_contributor_or_public
@must_have_addon(SHORT_NAME, 'node')
def weko_root_folder(node_addon, auth, **kwargs):
    return _weko_root_folder(node_addon, auth=auth)

def _get_path(indices, index_id):
    index = filter(lambda i: str(i.identifier) == str(index_id), indices)[0]
    if index.parentIdentifier is None:
        return '/{}/'.format(index_id)
    else:
        return '{}{}/'.format(_get_path(indices, index.parentIdentifier),
                              index_id)
