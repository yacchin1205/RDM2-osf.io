import re
import httplib

from swiftclient import Connection
#from swiftclient import exceptions as swift_exceptions

from framework.exceptions import HTTPError
from website.addons.base.exceptions import InvalidAuthError, InvalidFolderError
from website.addons.swift.settings import BUCKET_LOCATIONS

from website.addons.swift.provider import SwiftProvider

def connect_swift(access_key=None, secret_key=None, tenant_name=None, node_settings=None):
    """Helper to build an swiftclient.Connection object
    """
    if node_settings is not None:
        if node_settings.external_account is not None:
            provider = SwiftProvider(node_settings.external_account)
            access_key, secret_key, tenant_name = provider.username, provider.password, provider.host
    connection = Connection(auth_version='2',
                            authurl='http://inter-auth.ecloud.nii.ac.jp:5000/v2.0/',
                            user=access_key,
                            key=secret_key,
                            tenant_name=tenant_name)
    return connection


def get_bucket_names(node_settings):
    try:
        headers, containers = connect_swift(node_settings=node_settings).get_account()
        return list(map(lambda c: c['name'], containers))
    except swift_exceptions.ClientException as e:
        raise HTTPError(e.http_status)

    return [bucket.name for bucket in buckets]


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
    return connect_swift(node_settings=node_settings).put_container(container_name)


def container_exists(access_key, secret_key, tenant_name, container_name):
    """Tests for the existance of a bucket and if the user
    can access it with the given keys
    """
    if not container_name:
        return False

    connection = connect_swift(access_key, secret_key, tenant_name)

    try:
        # Will raise an exception if container_name doesn't exist
        connect_swift(access_key, secret_key, tenant_name).head_container(container_name)
    except exception.S3ResponseError as e:
        if e.status not in (301, 302):
            return False
    return True


def can_list(access_key, secret_key, tenant_name):
    """Return whether or not a user can list
    all buckets accessable by this keys
    """
    # Bail out early as boto does not handle getting
    # Called with (None, None)
    if not (access_key and secret_key and tenant_name):
        return False

    try:
        connect_swift(access_key, secret_key, tenant_name).get_account()
    except exception.S3ResponseError:
        return False
    return True

def get_user_info(access_key, secret_key, tenant_name):
    """Returns an NII Swift User with .display_name and .id, or None
    """
    if not (access_key and secret_key and tenant_name):
        return None

    return {'display_name': access_key, 'id': access_key}
