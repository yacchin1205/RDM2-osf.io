import re
import httplib

from azure.storage.blob import BlockBlobService
from azure.common import AzureHttpError

from framework.exceptions import HTTPError
from website.addons.base.exceptions import InvalidAuthError, InvalidFolderError
from website.addons.azureblobstorage.settings import BUCKET_LOCATIONS

from website.addons.azureblobstorage.provider import AzureBlobStorageProvider

def connect_azureblobstorage(account_name=None, account_key=None, node_settings=None):
    """Helper to build an azureblobstorageclient.Connection object
    """
    if node_settings is not None:
        if node_settings.external_account is not None:
            account = node_settings.external_account
            account_name, account_key = account.oauth_key, account.oauth_secret
    service = BlockBlobService(account_name=account_name, account_key=account_key)
    return service


def get_bucket_names(node_settings):
    try:
        containers = connect_azureblobstorage(node_settings=node_settings).list_containers()
        return list(map(lambda c: c.name, containers))
    except AzureHttpError as e:
        raise HTTPError(e.status_code)


def validate_bucket_name(name):
    """Make sure the bucket name conforms to Amazon's expectations as described at:
    http://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html#bucketnamingrules
    The laxer rules for US East (N. Virginia) are not supported.
    """
    label = '[a-z0-9]+(?:[a-z0-9\-]*[a-z0-9])?'
    validate_name = re.compile('^' + label + '(?:\\.' + label + ')*$')
    is_ip_address = re.compile('^[0-9]+(?:\.[0-9]+){3}$')
    return (
        len(name) >= 3 and len(name) <= 63 and bool(validate_name.match(name)) and not bool(is_ip_address.match(name))
    )


def create_container(node_settings, container_name):
    return connect_azureblobstorage(node_settings=node_settings).put_container(container_name)


def container_exists(access_key, secret_key, container_name):
    """Tests for the existance of a bucket and if the user
    can access it with the given keys
    """
    if not container_name:
        return False

    connection = connect_azureblobstorage(access_key, secret_key)

    try:
        # Will raise an exception if container_name doesn't exist
        connection.get_container_properties(container_name)
    except AzureHttpError as e:
        if e.status_code not in (301, 302):
            return False
    return True


def can_list(access_key, secret_key):
    """Return whether or not a user can list
    all buckets accessable by this keys
    """
    # Bail out early as boto does not handle getting
    # Called with (None, None)
    if not (access_key and secret_key):
        return False

    try:
        connect_azureblobstorage(access_key, secret_key).list_containers()
    except AzureHttpError:
        return False
    return True

def get_user_info(account_name, account_key):
    """Returns an Azure Blob Storage User with .display_name and .id, or None
    """
    if not (account_name and account_key):
        return None

    return {'display_name': account_name, 'id': account_name}
