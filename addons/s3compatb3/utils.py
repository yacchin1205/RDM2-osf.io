import re

import boto3
from botocore import exceptions
from botocore.config import Config
from rest_framework import status as http_status

import addons.s3compatb3.settings as settings
from addons.base.exceptions import InvalidAuthError, InvalidFolderError
from framework.exceptions import HTTPError


def _endpoint(host):
    if not host:
        raise ValueError('host is required')

    port = 443
    match = re.match(r'^(.+):([0-9]+)$', host)
    if match is not None:
        host = match.group(1)
        port = int(match.group(2))

    scheme = 'https' if port == 443 else 'http'
    endpoint_url = f'{scheme}://{host}:{port}'
    region = host.split('.')[-3] if host.endswith('.oraclecloud.com') else None
    return endpoint_url, region


def connect_s3compatb3(host=None, access_key=None, secret_key=None, node_settings=None):
    """Build a Signature V4 S3 client for Oracle Object Storage."""
    if node_settings is not None and node_settings.external_account is not None:
        host = node_settings.external_account.provider_id.split('\t')[0]
        access_key = node_settings.external_account.oauth_key
        secret_key = node_settings.external_account.oauth_secret

    endpoint_url, region = _endpoint(host)
    return boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        endpoint_url=endpoint_url,
        config=Config(signature_version='s3v4'),
    )


def _status_for_error(error):
    return error.response['ResponseMetadata']['HTTPStatusCode']


def get_bucket_names(node_settings):
    try:
        response = connect_s3compatb3(node_settings=node_settings).list_buckets()
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
    client = connect_s3compatb3(node_settings=node_settings)
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
        connect_s3compatb3(host, access_key, secret_key).head_bucket(Bucket=bucket_name)
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
        connect_s3compatb3(host, access_key, secret_key).list_buckets()
    except (exceptions.BotoCoreError, exceptions.ClientError):
        return False
    return True


def get_user_info(host, access_key, secret_key):
    """Validate credentials and return the connected client, or None."""
    if not (host and access_key and secret_key):
        return None

    try:
        client = connect_s3compatb3(host, access_key, secret_key)
        client.list_buckets()
        return client
    except (exceptions.BotoCoreError, exceptions.ClientError):
        return None


def get_bucket_location_or_error(host, access_key, secret_key, bucket_name):
    """Return the bucket region reported by Oracle Object Storage."""
    try:
        response = connect_s3compatb3(host, access_key, secret_key).head_bucket(
            Bucket=bucket_name,
        )
    except exceptions.NoCredentialsError:
        raise InvalidAuthError()
    except exceptions.BotoCoreError:
        raise InvalidAuthError()
    except exceptions.ClientError:
        raise InvalidFolderError()

    headers = response['ResponseMetadata']['HTTPHeaders']
    return headers.get('x-amz-bucket-region', '')
