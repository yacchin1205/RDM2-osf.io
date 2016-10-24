"""Views for the node settings page."""
# -*- coding: utf-8 -*-
import datetime
import httplib as http
from requests.exceptions import SSLError

from flask import request
from modularodm import Q
from modularodm.storage.base import KeyExistsException

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from website.addons.base import generic_views
from website.addons.weko import client
from website.addons.weko.model import WEKOProvider
from website.addons.weko.serializer import DataverseSerializer
from dataverse.exceptions import VersionJsonNotFoundError
from website.oauth.models import ExternalAccount
from website.project.decorators import (
    must_have_addon, must_be_addon_authorizer,
    must_have_permission, must_not_be_registration,
    must_be_contributor_or_public
)
from website.util import rubeus, api_url_for
from website.util.sanitize import assert_clean

SHORT_NAME = 'weko'
FULL_NAME = 'WEKO'

weko_account_list = generic_views.account_list(
    SHORT_NAME,
    DataverseSerializer
)

weko_import_auth = generic_views.import_auth(
    SHORT_NAME,
    DataverseSerializer
)

weko_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

weko_get_config = generic_views.get_config(
    SHORT_NAME,
    DataverseSerializer
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
    """Saves selected Dataverse and dataset to node settings"""

    user_settings = node_addon.user_settings
    user = auth.user

    if user_settings and user_settings.owner != user:
        raise HTTPError(http.FORBIDDEN)

    try:
        assert_clean(request.json)
    except AssertionError:
        # TODO: Test me!
        raise HTTPError(http.NOT_ACCEPTABLE)

    alias = request.json.get('dataverse', {}).get('alias')
    doi = request.json.get('dataset', {}).get('doi')

    if doi is None or alias is None:
        return HTTPError(http.BAD_REQUEST)

    connection = client.connect_from_settings(node_addon)
    weko = client.get_weko(connection, alias)
    dataset = client.get_dataset(weko, doi)

    node_addon.set_folder(weko, dataset, auth)

    return {'dataverse': weko[1], 'dataset': dataset['title']}, http.OK


@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'user')
@must_have_addon(SHORT_NAME, 'node')
def weko_get_datasets(node_addon, **kwargs):
    """Get list of datasets from provided Dataverse alias"""
    alias = request.json.get('alias')

    connection = client.connect_from_settings(node_addon)
    weko = client.get_weko(connection, alias)
    datasets = client.get_datasets(weko)
    ret = {
        'alias': alias,  # include alias to verify dataset container
        'datasets': [{'title': dataset['title'], 'doi': dataset['href']} for dataset in datasets],
    }
    return ret, http.OK

## Crud ##


@must_have_permission('write')
@must_not_be_registration
@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def weko_publish_dataset(node_addon, auth, **kwargs):
    node = node_addon.owner
    publish_both = request.json.get('publish_both', False)

    now = datetime.datetime.utcnow()

    connection = client.connect_from_settings_or_401(node_addon)

    weko = client.get_weko(connection, node_addon.weko_alias)
    dataset = client.get_dataset(weko, node_addon.dataset_doi)

    if publish_both:
        client.publish_weko(dataverse)
    client.publish_dataset(dataset)

    # Add a log
    node.add_log(
        action='weko_dataset_published',
        params={
            'project': node.parent_id,
            'node': node._id,
            'dataset': dataset.title,
        },
        auth=auth,
        log_date=now,
    )

    return {'dataset': dataset.title}, http.OK

## HGRID ##

def _weko_root_folder(node_addon, auth, **kwargs):
    node = node_addon.owner

    # Quit if no dataset linked
    if not node_addon.complete:
        return []

    connection = client.connect_from_settings(node_addon)
    weko = client.get_weko(connection, node_addon.weko_alias)
    dataset = client.get_dataset(weko, node_addon.dataset_doi)

    # Quit if doi does not produce a dataset
    if dataset is None:
        return []

    return [rubeus.build_addon_root(
        node_addon,
        node_addon.dataset,
        permissions=[],
        dataset=node_addon.dataset,
        doi=dataset['href'],
        weko=weko[1],
        private_key=kwargs.get('view_only', None),
    )]


@must_be_contributor_or_public
@must_have_addon(SHORT_NAME, 'node')
def weko_root_folder(node_addon, auth, **kwargs):
    return _weko_root_folder(node_addon, auth=auth)

## Widget ##

@must_be_contributor_or_public
@must_have_addon(SHORT_NAME, 'node')
def weko_widget(node_addon, **kwargs):

    node = node_addon.owner
    widget_url = node.api_url_for('weko_get_widget_contents')

    ret = {
        'complete': node_addon.complete,
        'widget_url': widget_url,
    }
    ret.update(node_addon.config.to_json())

    return ret, http.OK


@must_be_contributor_or_public
@must_have_addon(SHORT_NAME, 'node')
def weko_get_widget_contents(node_addon, **kwargs):

    data = {
        'connected': False,
    }

    if not node_addon.complete:
        return {'data': data}, http.OK

    doi = node_addon.dataset_doi
    alias = node_addon.weko_alias

    connection = client.connect_from_settings_or_401(node_addon)
    weko = client.get_weko(connection, alias)
    dataset = client.get_dataset(weko, doi)

    if dataset is None:
        return {'data': data}, http.BAD_REQUEST

    weko_host = node_addon.external_account.oauth_key
    weko_url = 'TODO' # TODO
    dataset_url = 'TODO' # TODO

    data.update({
        'connected': True,
        'dataverse': node_addon.dataverse,
        'dataverseUrl': weko_url,
        'dataset': node_addon.dataset,
        'doi': doi,
        'datasetUrl': dataset_url,
        'citation': []
    })
    return {'data': data}, http.OK
