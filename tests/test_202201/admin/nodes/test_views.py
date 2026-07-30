import datetime

from unittest import mock
import pytest
import pytz
from admin.nodes.views import NodeDeleteView
from admin_tests.utilities import setup_log_view
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from osf.models import AdminLogEntry
from osf_tests.factories import ProjectFactory, NodeFactory
from tests.base import AdminTestCase


@pytest.mark.skip('Clone test case from admin_tests/nodes/test_views.py for making coverage')
class TestNodeDeleteView(AdminTestCase):
    def setUp(self):
        super(TestNodeDeleteView, self).setUp()
        self.node = ProjectFactory()
        self.request = RequestFactory().post('/fake_path')
        self.plain_view = NodeDeleteView
        self.view = setup_log_view(self.plain_view(), self.request,
                                   guid=self.node._id)

        self.url = reverse('nodes:remove', kwargs={'guid': self.node._id})

    @mock.patch('website.util.quota.update_user_used_quota')
    def test_remove_node(self, mock_update_user_used_quota_method):
        count = AdminLogEntry.objects.count()
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            self.view.delete(self.request)
        self.node.refresh_from_db()
        assert (self.node.is_deleted)
        assert (AdminLogEntry.objects.count()) == (count + 1)
        assert (self.node.deleted) == (mock_now)
        mock_update_user_used_quota_method.assert_called()

    @mock.patch('website.util.quota.update_user_used_quota')
    def test_remove_node_is_not_project_type(self, mock_update_user_used_quota_method):
        node = NodeFactory()
        self.view = setup_log_view(self.plain_view(), self.request,
                                   guid=node._id)
        count = AdminLogEntry.objects.count()
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            self.view.delete(self.request)
        node.refresh_from_db()
        assert (node.is_deleted)
        assert (AdminLogEntry.objects.count()) == (count + 1)
        assert (node.deleted) == (mock_now)
        mock_update_user_used_quota_method.assert_not_called()

    @mock.patch('website.util.quota.update_user_used_quota')
    def test_restore_node(self, mock_update_user_used_quota_method):
        self.view.delete(self.request)
        self.node.refresh_from_db()
        assert (self.node.is_deleted)
        assert (self.node.deleted is not None)
        count = AdminLogEntry.objects.count()
        self.view.delete(self.request)
        self.node.reload()
        assert not (self.node.is_deleted)
        assert (self.node.deleted is None)
        assert (AdminLogEntry.objects.count()) == (count + 1)
        mock_update_user_used_quota_method.assert_called()

    @mock.patch('website.util.quota.update_user_used_quota')
    def test_restore_node_is_not_project_type(self, mock_update_user_used_quota_method):
        node = NodeFactory()
        self.view = setup_log_view(self.plain_view(), self.request,
                                   guid=node._id)
        self.view.delete(self.request)
        node.refresh_from_db()
        assert (node.is_deleted)
        assert (node.deleted is not None)
        count = AdminLogEntry.objects.count()
        self.view.delete(self.request)
        node.reload()
        assert not (node.is_deleted)
        assert (node.deleted is None)
        assert (AdminLogEntry.objects.count()) == (count + 1)
        mock_update_user_used_quota_method.assert_not_called()
