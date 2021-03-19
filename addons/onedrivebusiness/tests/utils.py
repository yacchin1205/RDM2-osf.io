# -*- coding: utf-8 -*-
from nose.tools import (assert_equals, assert_true, assert_false)

from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.onedrivebusiness.tests.factories import OneDriveBusinessAccountFactory
from addons.onedrivebusiness.provider import OneDriveBusinessProvider
from addons.onedrivebusiness.serializer import OneDriveBusinessSerializer
from addons.onedrivebusiness import utils

class OneDriveBusinessAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'onedrivebusiness'
    ExternalAccountFactory = OneDriveBusinessAccountFactory
    Provider = OneDriveBusinessProvider
    Serializer = OneDriveBusinessSerializer
    client = None
    folder = {
        'path': 'bucket',
        'name': 'bucket',
        'id': 'bucket'
    }

    def test_https(self):
        connection = utils.connect_onedrivebusiness(host='securehost',
                                            access_key='a',
                                            secret_key='s')
        assert_true(connection.is_secure)
        assert_equals(connection.host, 'securehost')
        assert_equals(connection.port, 443)

        connection = utils.connect_onedrivebusiness(host='securehost:443',
                                            access_key='a',
                                            secret_key='s')
        assert_true(connection.is_secure)
        assert_equals(connection.host, 'securehost')
        assert_equals(connection.port, 443)

    def test_http(self):
        connection = utils.connect_onedrivebusiness(host='normalhost:80',
                                            access_key='a',
                                            secret_key='s')
        assert_false(connection.is_secure)
        assert_equals(connection.host, 'normalhost')
        assert_equals(connection.port, 80)

        connection = utils.connect_onedrivebusiness(host='normalhost:8080',
                                            access_key='a',
                                            secret_key='s')
        assert_false(connection.is_secure)
        assert_equals(connection.host, 'normalhost')
        assert_equals(connection.port, 8080)
