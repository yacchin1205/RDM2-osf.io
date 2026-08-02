import re
from dataclasses import dataclass

import boto3
from botocore import exceptions
from botocore.config import Config
from rest_framework import status as http_status

import addons.s3compat.settings as settings
from addons.base.exceptions import InvalidAuthError, InvalidFolderError
from framework.exceptions import HTTPError


def _endpoint_url(host):
    if not host:
        raise ValueError('host is required')

    port = 443
    match = re.match(r'^(.+):([0-9]+)$', host)
    if match is not None:
        host = match.group(1)
        port = int(match.group(2))

    scheme = 'https' if port == 443 else 'http'
    return f'{scheme}://{host}:{port}'


def connect_s3compat(host=None, access_key=None, secret_key=None, node_settings=None):
    """Build an S3 client using Signature V4."""
    if node_settings is not None and node_settings.external_account is not None:
        host = node_settings.external_account.provider_id.split('\t')[0]
        access_key = node_settings.external_account.oauth_key
        secret_key = node_settings.external_account.oauth_secret

    return boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=_endpoint_url(host),
        config=Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'},
        ),
    )


def _status_for_error(error):
    return error.response['ResponseMetadata']['HTTPStatusCode']


def get_bucket_names(node_settings):
    try:
        response = connect_s3compat(node_settings=node_settings).list_buckets()
    except exceptions.NoCredentialsError:
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)
    except exceptions.ClientError as error:
        raise HTTPError(_status_for_error(error))
    except exceptions.BotoCoreError:
        raise HTTPError(http_status.HTTP_502_BAD_GATEWAY)

    return [bucket['Name'] for bucket in response.get('Buckets', [])]


def find_service_by_host(host):
    services = [service for service in settings.AVAILABLE_SERVICES if service['host'] == host]
    if not services:
        raise KeyError(host)
    return services[0]


def validate_bucket_location(node_settings, location):
    if location == '':
        return True
    host = node_settings.external_account.provider_id.split('\t')[0]
    service = find_service_by_host(host)
    return location in service['bucketLocations']


def validate_bucket_name(name):
    """Validate a bucket name against the S3 DNS naming rules."""
    label = r'[a-z0-9]+(?:[a-z0-9\-]*[a-z0-9])?'
    validate_name = re.compile('^' + label + '(?:\\.' + label + ')*$')
    is_ip_address = re.compile(r'^[0-9]+(?:\.[0-9]+){3}$')
    return (
        3 <= len(name) <= 63
        and bool(validate_name.match(name))
        and not bool(is_ip_address.match(name))
    )


def create_bucket(node_settings, bucket_name, location=''):
    client = connect_s3compat(node_settings=node_settings)
    if not location:
        return client.create_bucket(Bucket=bucket_name)
    return client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={'LocationConstraint': location},
    )


def bucket_exists(host, access_key, secret_key, bucket_name):
    """Return whether a bucket exists and is accessible with the credentials."""
    if not bucket_name:
        return False

    try:
        connect_s3compat(host, access_key, secret_key).head_bucket(Bucket=bucket_name)
    except exceptions.ClientError as error:
        if _status_for_error(error) not in (301, 302):
            return False
    except exceptions.BotoCoreError:
        return False
    return True


def can_list(host, access_key, secret_key):
    """Return whether the credentials can list buckets."""
    if not (host and access_key and secret_key):
        return False

    try:
        connect_s3compat(host, access_key, secret_key).list_buckets()
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


def get_user_info(host, access_key, secret_key):
    """Return S3-compatible storage owner information, or None."""
    if not (host and access_key and secret_key):
        return None

    try:
        response = connect_s3compat(host, access_key, secret_key).list_buckets()
        return Owner.from_dict(response['Owner'])
    except (exceptions.BotoCoreError, exceptions.ClientError, KeyError):
        return None


def get_bucket_location_or_error(host, access_key, secret_key, bucket_name):
    """Return a bucket location or raise the add-on's authentication/folder error."""
    try:
        client = connect_s3compat(host, access_key, secret_key)
        client.head_bucket(Bucket=bucket_name)
    except exceptions.NoCredentialsError:
        raise InvalidAuthError()
    except exceptions.BotoCoreError:
        raise InvalidAuthError()
    except exceptions.ClientError:
        raise InvalidFolderError()

    try:
        response = client.get_bucket_location(Bucket=bucket_name)
    except exceptions.ClientError:
        return ''
    return response.get('LocationConstraint') or ''
