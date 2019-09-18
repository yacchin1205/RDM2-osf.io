# -*- coding: utf-8 -*-
"""Utility functions for the IQB-RIMS add-on.
"""
from datetime import datetime
import functools
import hashlib
import httplib as http
import json
import logging
import os

from django.db.models import Subquery
from flask import request

from addons.base import exceptions
from addons.iqbrims.apps import IQBRIMSAddonConfig
from addons.iqbrims.client import (
    IQBRIMSClient,
    SpreadsheetClient,
)
from addons.iqbrims import settings
from framework.exceptions import HTTPError
from osf.models import (
    Guid, Comment, ExternalAccount, RdmAddonOption
)
from website.util import api_v2_url
from website import settings as ws_settings

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

def copy_node_auth(node, other_node_addon):
    node_addon = node.get_or_add_addon(IQBRIMSAddonConfig.short_name)

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
    content = u'**{title}** {body}'.format(title=title, body=body)
    target = Guid.load(node._id)
    comment = Comment(user=user, node=node, content=content,
                      target=target, root_target=target)
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

def get_management_node(node):
    inst_ids = node.affiliated_institutions.values('id')
    try:
        opt = RdmAddonOption.objects.filter(
            provider=IQBRIMSAddonConfig.short_name,
            institution_id__in=Subquery(inst_ids),
            management_node__isnull=False,
            is_allowed=True
        ).first()
        if opt is None:
            return None
    except RdmAddonOption.DoesNotExist:
        return None
    return opt.management_node

def iqbrims_update_spreadsheet(node, management_node, register_type, status):
    iqbrims_config = ws_settings.ADDONS_AVAILABLE_DICT[IQBRIMSAddonConfig.short_name]
    management_node_addon = iqbrims_config.node_settings.objects.get(owner=management_node)
    if management_node_addon is None:
        raise HTTPError(http.BAD_REQUEST, 'IQB-RIMS addon disabled in management node')
    folder_id = management_node_addon.folder_id
    try:
        access_token = management_node_addon.fetch_access_token()
    except exceptions.InvalidAuthError:
        raise HTTPError(403)
    client = IQBRIMSClient(access_token)
    _, rootr = client.create_folder_if_not_exists(folder_id, register_type)
    _, r = client.create_spreadsheet_if_not_exists(rootr['id'],
                                                   settings.APPSHEET_FILENAME)
    sclient = SpreadsheetClient(r['id'], access_token)
    sheets = [s
              for s in sclient.sheets()
              if s['properties']['title'] == settings.APPSHEET_SHEET_NAME]
    logger.info('Spreadsheet: id={}, sheet={}'.format(r['id'], sheets))
    if len(sheets) == 0:
        sclient.add_sheet(settings.APPSHEET_SHEET_NAME)
        sheets = [s
                  for s in sclient.sheets()
                  if s['properties']['title'] == settings.APPSHEET_SHEET_NAME]
    assert len(sheets) == 1
    sheet_id = sheets[0]['properties']['title']
    acolumns = settings.APPSHEET_DEPOSIT_COLUMNS \
        if register_type == 'deposit' \
        else settings.APPSHEET_CHECK_COLUMNS
    columns = sclient.ensure_columns(sheet_id,
                                     [c for c, __ in acolumns])
    column_index = columns.index([c for c, cid in acolumns
                                  if cid == '_node_id'][0])
    row_max = sheets[0]['properties']['gridProperties']['rowCount']
    values = sclient.get_row_values(sheet_id, column_index, row_max)
    logger.info('IDs: {}'.format(values))
    iqbrims = node.get_addon('iqbrims')
    folder_link = client.get_folder_link(iqbrims.folder_id)
    logger.info('Link: {}'.format(folder_link))
    if node._id not in values:
        logger.info('Inserting: {}'.format(node._id))
        v = iqbrims_fill_spreadsheet_values(node, status, folder_link,
                                            columns, ['' for c in columns])
        sclient.add_row(sheet_id, v)
    else:
        logger.info('Updating: {}'.format(node._id))
        row_index = values.index(node._id)
        v = sclient.get_row(sheet_id, row_index, len(columns))
        v += ['' for __ in range(len(v), len(columns))]
        v = iqbrims_fill_spreadsheet_values(node, status, folder_link,
                                            columns, v)
        sclient.update_row(sheet_id, v, row_index)

def iqbrims_filled_index(access_token, f):
    sclient = SpreadsheetClient(f['id'], access_token)
    sheets = [s
              for s in sclient.sheets()
              if s['properties']['title'] == settings.INDEXSHEET_SHEET_NAME]
    assert len(sheets) == 1
    sheet_props = sheets[0]['properties']
    sheet_id = sheet_props['title']
    col_count = sheet_props['gridProperties']['columnCount']
    row_count = sheet_props['gridProperties']['rowCount']
    logger.info('Grid: {}, {}'.format(col_count, row_count))
    columns = sclient.get_column_values(sheet_id, 1, col_count)
    fills = sclient.get_row_values(sheet_id, columns.index('Filled'), 2)
    procs = [fill for fill in fills if fill != 'TRUE']
    return len(procs) == 0

def iqbrims_fill_spreadsheet_values(node, status, folder_link, columns, values):
    assert len(columns) == len(values), values
    acolumns = settings.APPSHEET_DEPOSIT_COLUMNS \
        if status['state'] == 'deposit' \
        else settings.APPSHEET_CHECK_COLUMNS
    values = list(values)
    for i, col in enumerate(columns):
        tcols = [cid for c, cid in acolumns if c == col]
        if len(tcols) == 0:
            continue
        tcol = tcols[0]
        if tcol is None:
            pass
        elif tcol == '_updated':
            values[i] = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        elif tcol == '_node_id':
            values[i] = node._id
        elif tcol == '_node_owner':
            values[i] = node.creator.fullname
        elif tcol == '_node_mail':
            values[i] = node.creator.username
        elif tcol == '_node_title':
            values[i] = node.title
        elif tcol == '_labo_name':
            labos = [l['text']
                     for l in settings.LABO_LIST
                     if l['id'] == status['labo_id']]
            values[i] = labos[0] if len(labos) > 0 \
                else 'Unknown ID: {}'.format(status['labo_id'])
        elif tcol == '_drive_url':
            values[i] = folder_link
        else:
            assert not tcol.startswith('_')
            values[i] = status[tcol] if tcol in status else ''
    return values
