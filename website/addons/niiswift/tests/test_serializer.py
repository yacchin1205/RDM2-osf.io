# -*- coding: utf-8 -*-
"""Serializer tests for the S3 addon."""
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from website.util import web_url_for
from website.addons.base.testing.serializers import StorageAddonSerializerTestSuiteMixin
from website.addons.niiswift.tests.factories import SwiftAccountFactory
from website.addons.niiswift.serializer import SwiftSerializer

from tests.base import OsfTestCase


class TestSwiftSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 'niiswift'
    Serializer = SwiftSerializer
    ExternalAccountFactory = SwiftAccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid

    def setUp(self):
        self.mock_can_list = mock.patch('website.addons.niiswift.serializer.utils.can_list')
        self.mock_can_list.return_value = True
        self.mock_can_list.start()
        super(TestSwiftSerializer, self).setUp()

    def tearDown(self):
        self.mock_can_list.stop()
        super(TestSwiftSerializer, self).tearDown()