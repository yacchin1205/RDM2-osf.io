import re
from dataclasses import dataclass

from rest_framework import status as http_status

import boto3
from botocore import exceptions

from framework.exceptions import HTTPError
from addons.base.exceptions import InvalidAuthError, InvalidFolderError
from addons.s3.settings import BUCKET_LOCATIONS


def connect_s3(access_key=None, secret_key=None, node_settings=None):
    """Helper to build an S3Connection object
    Can be used to change settings on all S3Connections
    See: CallingFormat
    """
    if node_settings is not None:
        if node_settings.external_account is not None:
            access_key, secret_key = node_settings.external_account.oauth_key, node_settings.external_account.oauth_secret
    return boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def get_status_for_error(error):
    return error.response['ResponseMetadata']['HTTPStatusCode']


def get_bucket_names(node_settings):
    try:
        response = connect_s3(node_settings=node_settings).list_buckets()
    except exceptions.NoCredentialsError:
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)
    except exceptions.ClientError as error:
        raise HTTPError(get_status_for_error(error))

    return [bucket['Name'] for bucket in response['Buckets']]


def validate_bucket_location(location):
    return location in BUCKET_LOCATIONS


def validate_bucket_name(name):
    """Make sure the bucket name conforms to Amazon's expectations as described at:
    http://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html#bucketnamingrules
    The laxer rules for US East (N. Virginia) are not supported.
    """
    label = r'[a-z0-9]+(?:[a-z0-9\-]*[a-z0-9])?'
    validate_name = re.compile('^' + label + '(?:\\.' + label + ')*$')
    is_ip_address = re.compile(r'^[0-9]+(?:\.[0-9]+){3}$')
    return (
        len(name) >= 3 and len(name) <= 63 and bool(validate_name.match(name)) and not bool(is_ip_address.match(name))
    )


def create_bucket(node_settings, bucket_name, location=''):
    client = connect_s3(node_settings=node_settings)
    if not location or location == 'us-east-1':
        return client.create_bucket(Bucket=bucket_name)
    return client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={'LocationConstraint': location},
    )


def bucket_exists(access_key, secret_key, bucket_name):
    """Tests for the existance of a bucket and if the user
    can access it with the given keys
    """
    if not bucket_name:
        return False

    bucket_name = bucket_name.lower()

    try:
        # Will raise an exception if bucket_name doesn't exist
        connect_s3(access_key, secret_key).head_bucket(Bucket=bucket_name)
    except exceptions.ClientError as error:
        if get_status_for_error(error) not in (301, 302):
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
        connect_s3(access_key, secret_key).list_buckets()
    except (exceptions.BotoCoreError, exceptions.ClientError):
        return False
    return True


@dataclass(slots=True, frozen=True)
class Owner:
    display_name: str
    id: str

    @classmethod
    def from_dict(cls, data):
        owner_id = data['ID']
        return cls(data.get('DisplayName') or owner_id, owner_id)


def get_user_info(access_key, secret_key):
    """Returns an S3 User with .display_name and .id, or None
    """
    if not (access_key and secret_key):
        return None

    try:
        response = connect_s3(access_key, secret_key).list_buckets()
        return Owner.from_dict(response['Owner'])
    except (exceptions.BotoCoreError, exceptions.ClientError, KeyError):
        return None

def get_bucket_location_or_error(access_key, secret_key, bucket_name):
    """Returns the location of a bucket or raises AddonError
    """
    bucket_name = bucket_name.lower()

    try:
        # Will raise an exception if bucket_name doesn't exist
        response = connect_s3(access_key, secret_key).get_bucket_location(Bucket=bucket_name)
        return response['LocationConstraint']
    except exceptions.NoCredentialsError:
        raise InvalidAuthError()
    except (exceptions.BotoCoreError, exceptions.ClientError):
        raise InvalidFolderError()
