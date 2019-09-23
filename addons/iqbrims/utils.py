# -*- coding: utf-8 -*-
"""Utility functions for the IQB-RIMS add-on.
"""
import functools
import hashlib
import httplib as http
import json
import logging
import os

from flask import request

from addons.iqbrims.apps import IQBRIMSAddonConfig
from framework.exceptions import HTTPError
from osf.models import Comment, ExternalAccount
from website.util import api_v2_url

logger = logging.getLogger(__name__)
_log_actions = None


def get_log_actions():
    global _log_actions
    if _log_actions is not None:
        return _log_actions
    HERE = os.path.dirname(os.path.abspath(__file__))
    STATIC_PATH = os.path.join(HERE, 'static')
    with open(os.path.join(STATIC_PATH, 'iqbrimsLogActionList.json')) as fp:
        _log_actions = json.load(fp)
    return _log_actions

def build_iqbrims_urls(item, node, path):
    return {
        'fetch': api_v2_url('nodes/{}/addons/iqbrims/folders/'.format(node._id), params={'path': path}),
        'folders': api_v2_url('nodes/{}/addons/iqbrims/folders/'.format(node._id), params={'path': path, 'id': item['id']})
    }

def to_hgrid(item, node, path):
    """
    :param item: contents returned from IQB-RIMS API
    :return: results formatted as required for Hgrid display
    """
    path = os.path.join(path, item['title'])

    serialized = {
        'path': path,
        'id': item['id'],
        'kind': 'folder',
        'name': item['title'],
        'addon': 'iqbrims',
        'urls': build_iqbrims_urls(item, node, path=path)
    }
    return serialized

def serialize_iqbrims_widget(node):
    iqbrims = node.get_addon('iqbrims')
    ret = {
        'complete': True,
        'include': False,
        'can_expand': True,
    }
    ret.update(iqbrims.config.to_json())
    return ret

def oauth_disconnect_following_other(user, other_user_addon):
    user_addon = user.get_addon(IQBRIMSAddonConfig.short_name)

    for account in user_addon.external_accounts.all():
        exists = other_user_addon.external_accounts.filter(provider_id=account.provider_id).exists()
        if not exists:
            user_addon.revoke_oauth_access(account)
            user_addon.save()
            user.external_accounts.remove(account)
            user.save()

def copy_node_auth(node, other_node_addon, auth):
    node_addon = node.get_or_add_addon(IQBRIMSAddonConfig.short_name, auth)

    # deauthorize node
    if other_node_addon.external_account is None or other_node_addon.user_settings is None:
        node_addon.deauthorize()
        node_addon.save()
        return

    user = other_node_addon.user_settings.owner

    # copy external_account
    account = create_or_update_external_account_with_other(other_node_addon.external_account)

    # add external_account to user and user_settings if it does not exist
    if not user.external_accounts.filter(id=account.id).exists():
        user.external_accounts.add(account)
        user.save()

    # set auth and folder to node_settings
    node_addon.set_auth(account, user)
    node_addon.set_folder({'id': other_node_addon.folder_id, 'path': other_node_addon.folder_path}, auth=None)
    node_addon.save()

def create_or_update_external_account_with_other(other_external_account):
    try:
        external_account = ExternalAccount.objects.get(
            provider=IQBRIMSAddonConfig.short_name,
            provider_id=other_external_account.provider_id
        )
    except BaseException:
        logger.exception('Unexpected error')
        external_account = None

    if external_account is None:
        external_account = ExternalAccount(
            scopes=other_external_account.scopes,
            provider_id=other_external_account.provider_id,
            oauth_key=other_external_account.oauth_key,
            provider=IQBRIMSAddonConfig.short_name,
            expires_at=other_external_account.expires_at,
            date_last_refreshed=other_external_account.date_last_refreshed,
            provider_name=IQBRIMSAddonConfig.full_name,
            refresh_token=other_external_account.refresh_token
        )
    else:
        external_account.scopes = other_external_account.scopes
        external_account.oauth_key = other_external_account.oauth_key
        external_account.expires_at = other_external_account.expires_at
        external_account.date_last_refreshed = other_external_account.date_last_refreshed
        external_account.refresh_token = other_external_account.refresh_token

    external_account.save()

    return external_account

def get_folder_title(node):
    return u'{0}-{1}'.format(node.title.replace('/', '_'), node._id)

def add_comment(node, user, title, body):
    content = '**{title}** {body}'.format(title=title, body=body)
    comment = Comment(user=user, node=node, content=content)
    comment.save()
    return comment

def must_have_valid_hash():
    """Decorator factory that ensures that a request have valid X-RDM-Token header.

    :returns: Decorator function

    """
    def wrapper(func):

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            owner = kwargs['node']
            addon = owner.get_addon(IQBRIMSAddonConfig.short_name)
            if addon is None:
                raise HTTPError(http.BAD_REQUEST)
            secret = addon.get_secret()
            process_def_id = addon.get_process_definition_id()
            valid_hash = hashlib.sha256((secret + process_def_id + owner._id).encode('utf8')).hexdigest()
            request_hash = request.headers.get('X-RDM-Token', None)
            logger.debug('must_have_valid_hash: request_hash={}'.format(request_hash))
            logger.debug('must_have_valid_hash: valid_hash={}'.format(valid_hash))
            if request_hash != valid_hash:
                raise HTTPError(
                    http.FORBIDDEN,
                    data={'message_long': ('User has restricted access to this page.')}
                )
            return func(*args, **kwargs)

        return wrapped

    return wrapper
