# -*- coding: utf-8 -*-
"""Serializer tests for the My MinIO addon."""
import mock
import pytest

from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.onedrivebusiness.tests.factories import OneDriveBusinessAccountFactory
from addons.onedrivebusiness.serializer import OneDriveBusinessSerializer

from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

class TestOneDriveBusinessSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 'onedrivebusiness'
    Serializer = OneDriveBusinessSerializer
    ExternalAccountFactory = OneDriveBusinessAccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid

    def setUp(self):
        self.mock_can_list = mock.patch('addons.onedrivebusiness.serializer.utils.can_list')
        self.mock_can_list.return_value = True
        self.mock_can_list.start()
        super(TestOneDriveBusinessSerializer, self).setUp()

    def tearDown(self):
        self.mock_can_list.stop()
        super(TestOneDriveBusinessSerializer, self).tearDown()
