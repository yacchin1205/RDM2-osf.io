import httplib

#from swiftclient import exceptions as swift_exceptions
from flask import request
from modularodm import Q
from modularodm.storage.base import KeyExistsException

from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

from website.addons.base import generic_views
from website.addons.swift import utils
from website.addons.swift.provider import SwiftProvider
from website.addons.swift.serializer import SwiftSerializer
from website.oauth.models import ExternalAccount
from website.project.decorators import (
    must_have_addon, must_have_permission,
    must_be_addon_authorizer,
)

SHORT_NAME = 'swift'
FULL_NAME = 'NII Swift'

swift_account_list = generic_views.account_list(
    SHORT_NAME,
    SwiftSerializer
)

swift_import_auth = generic_views.import_auth(
    SHORT_NAME,
    SwiftSerializer
)

swift_deauthorize_node = generic_views.deauthorize_node(
    SHORT_NAME
)

swift_get_config = generic_views.get_config(
    SHORT_NAME,
    SwiftSerializer
)

def _set_folder(node_addon, folder, auth):
    folder_id = folder['id']
    node_addon.set_folder(folder_id, auth=auth)
    node_addon.save()

swift_set_config = generic_views.set_config(
    SHORT_NAME,
    FULL_NAME,
    SwiftSerializer,
    _set_folder
)

@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def swift_folder_list(node_addon, **kwargs):
    """ Returns all the subsequent folders under the folder id passed.
    """
    return node_addon.get_folders()

swift_root_folder = generic_views.root_folder(
    SHORT_NAME
)

@must_be_logged_in
def swift_add_user_account(auth, **kwargs):
    """Verifies new external account credentials and adds to user's list"""
    try:
        access_key = request.json['access_key']
        secret_key = request.json['secret_key']
        tenant_name = request.json['tenant_name']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    if not (access_key and secret_key and tenant_name):
        return {
            'message': 'All the fields above are required.'
        }, httplib.BAD_REQUEST

    user_info = utils.get_user_info(access_key, secret_key, tenant_name)
    if not user_info:
        return {
            'message': ('Unable to access account.\n'
                'Check to make sure that the above credentials are valid, '
                'and that they have permission to list buckets.')
        }, httplib.BAD_REQUEST

    if not utils.can_list(access_key, secret_key, tenant_name):
        return {
            'message': ('Unable to list buckets.\n'
                'Listing buckets is required permission that can be changed via IAM')
        }, httplib.BAD_REQUEST

    provider = SwiftProvider(account=None, tenant_name=tenant_name,
                             username=access_key, password=secret_key)
    try:
        provider.account.save()
    except KeyExistsException:
        # ... or get the old one
        provider.account = ExternalAccount.find_one(
            Q('provider', 'eq', SHORT_NAME) &
            Q('provider_id', 'eq', '{}:{}'.format(tenant_name, access_key).lower())
        )
    assert provider.account is not None

    if provider.account not in auth.user.external_accounts:
        auth.user.external_accounts.append(provider.account)

    # Ensure NII Swift is enabled.
    auth.user.get_or_add_addon('swift', auth=auth)
    auth.user.save()

    return {}


@must_be_addon_authorizer(SHORT_NAME)
@must_have_addon('swift', 'node')
@must_have_permission('write')
def swift_create_container(auth, node_addon, **kwargs):
    bucket_name = request.json.get('bucket_name', '')

    if not utils.validate_bucket_name(bucket_name):
        return {
            'message': 'That bucket name is not valid.',
            'title': 'Invalid bucket name',
        }, httplib.BAD_REQUEST

    try:
        utils.create_container(node_addon, bucket_name)
    except exception.S3ResponseError as e:
        return {
            'message': e.message,
            'title': 'Problem connecting to Swift',
        }, httplib.BAD_REQUEST
    except exception.S3CreateError as e:
        return {
            'message': e.message,
            'title': "Problem creating bucket '{0}'".format(bucket_name),
        }, httplib.BAD_REQUEST
    except exception.BotoClientError as e:  # Base class catchall
        return {
            'message': e.message,
            'title': 'Error connecting to Swift',
        }, httplib.BAD_REQUEST

    return {}
