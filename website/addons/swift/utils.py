import re
import httplib

from boto import exception
from boto.s3.connection import S3Connection
from boto.s3.connection import OrdinaryCallingFormat

from swiftclient import Connection
# from swiftclient import exceptions

from framework.exceptions import HTTPError
from website.addons.base.exceptions import InvalidAuthError, InvalidFolderError
from website.addons.swift.settings import BUCKET_LOCATIONS


def connect_swift(access_key=None, secret_key=None, node_settings=None):
    """Helper to build an swiftclient.Connection object
    """
    if node_settings is not None:
        if node_settings.external_account is not None:
            access_key, secret_key = node_settings.external_account.oauth_key, node_settings.external_account.oauth_secret
    connection = Connection(auth_version='2',
                            authurl='http://inter-auth.ecloud.nii.ac.jp:5000/v2.0/',
                            user=access_key,
                            key=secret_key,
                            tenant_name='yamaji')
    return connection


def get_bucket_names(node_settings):
    try:
        headers, containers = connect_swift(node_settings=node_settings).get_account()
        return list(map(lambda c: c['name'], containers))
    except exceptions.ClientException:
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


def container_exists(access_key, secret_key, container_name):
    """Tests for the existance of a bucket and if the user
    can access it with the given keys
    """
    if not container_name:
        return False

    connection = connect_swift(access_key, secret_key)

    try:
        # Will raise an exception if container_name doesn't exist
        connect_swift(access_key, secret_key).head_container(container_name)
    except exception.S3ResponseError as e:
        if e.status not in (301, 302):
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
        connect_swift(access_key, secret_key).get_account()
    except exception.S3ResponseError:
        return False
    return True

def get_user_info(access_key, secret_key):
    """Returns an NII Swift User with .display_name and .id, or None
    """
    if not (access_key and secret_key):
        return None

    return {'display_name': access_key, 'id': access_key}
