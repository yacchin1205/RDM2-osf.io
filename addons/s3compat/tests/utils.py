# -*- coding: utf-8 -*-

from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.s3compat.tests.factories import S3CompatAccountFactory
from addons.s3compat.provider import S3CompatProvider
from addons.s3compat.serializer import S3CompatSerializer
from addons.s3compat import utils

class S3CompatAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 's3compat'
    ExternalAccountFactory = S3CompatAccountFactory
    Provider = S3CompatProvider
    Serializer = S3CompatSerializer
    client = None
    folder = {
        'path': 'bucket',
        'name': 'bucket',
        'id': 'bucket'
    }

    def test_https(self):
        connection = utils.connect_s3compat(host='securehost',
                                            access_key='a',
                                            secret_key='s')
        assert (connection.meta.endpoint_url) == ('https://securehost:443')

        connection = utils.connect_s3compat(host='securehost:443',
                                            access_key='a',
                                            secret_key='s')
        assert (connection.meta.endpoint_url) == ('https://securehost:443')

    def test_http(self):
        connection = utils.connect_s3compat(host='normalhost:80',
                                            access_key='a',
                                            secret_key='s')
        assert (connection.meta.endpoint_url) == ('http://normalhost:80')

        connection = utils.connect_s3compat(host='normalhost:8080',
                                            access_key='a',
                                            secret_key='s')
        assert (connection.meta.endpoint_url) == ('http://normalhost:8080')


def test_signature_version():
    connection = utils.connect_s3compat(host='securehost',
                                        access_key='a',
                                        secret_key='s')

    assert connection.meta.config.signature_version == 's3v4'
