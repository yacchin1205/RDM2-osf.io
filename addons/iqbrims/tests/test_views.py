# -*- coding: utf-8 -*-
import hashlib
import mock
from nose.tools import *  # noqa
import pytest
import re

from addons.base.tests.views import OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
from addons.iqbrims.tests.utils import mock_folders as sample_folder_data
from addons.iqbrims.tests.utils import IQBRIMSAddonTestCase
from osf.models import Comment
from osf_tests.factories import ProjectFactory
from tests.base import OsfTestCase
from addons.iqbrims.client import (
    IQBRIMSClient,
    IQBRIMSFlowableClient,
    SpreadsheetClient
)
from addons.iqbrims.serializer import IQBRIMSSerializer
import addons.iqbrims.views as iqbrims_views
from addons.iqbrims import settings
from website import mails

pytestmark = pytest.mark.django_db


class TestAuthViews(IQBRIMSAddonTestCase, OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):

    def setUp(self):
        super(TestAuthViews, self).setUp()
        self.mock_get_folder_info = mock.patch.object(
            IQBRIMSClient,
            'get_folder_info'
        )
        self.mock_get_folder_info.return_value = {'title': 'Test-xxxxx'}
        self.mock_get_folder_info.start()
        self.mock_rename_folder = mock.patch.object(
            IQBRIMSClient,
            'rename_folder'
        )
        self.mock_rename_folder.start()
        self.mock_fetch = mock.patch.object(
            self.node_settings.__class__,
            'fetch_access_token'
        )
        self.mock_fetch.return_value = self.external_account.oauth_key
        self.mock_fetch.start()

    def tearDown(self):
        self.mock_get_folder_info.stop()
        self.mock_rename_folder.stop()
        self.mock_fetch.stop()
        super(TestAuthViews, self).tearDown()

class TestConfigViews(IQBRIMSAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    folder = {
        'path': 'Drive/Camera Uploads',
        'id': '1234567890'
    }
    Serializer = IQBRIMSSerializer
    client = IQBRIMSClient

    def setUp(self):
        super(TestConfigViews, self).setUp()
        self.mock_about = mock.patch.object(
            IQBRIMSClient,
            'about'
        )
        self.mock_about.return_value = {'rootFolderId': '24601'}
        self.mock_about.start()
        self.mock_get_folder_info = mock.patch.object(
            IQBRIMSClient,
            'get_folder_info'
        )
        self.mock_get_folder_info.return_value = {'title': 'Test-xxxxx'}
        self.mock_get_folder_info.start()
        self.mock_rename_folder = mock.patch.object(
            IQBRIMSClient,
            'rename_folder'
        )
        self.mock_rename_folder.start()
        self.mock_fetch = mock.patch.object(
            self.node_settings.__class__,
            'fetch_access_token'
        )
        self.mock_fetch.return_value = self.external_account.oauth_key
        self.mock_fetch.start()

    def tearDown(self):
        self.mock_about.stop()
        self.mock_get_folder_info.stop()
        self.mock_rename_folder.stop()
        self.mock_fetch.stop()
        super(TestConfigViews, self).tearDown()

    @mock.patch.object(IQBRIMSClient, 'folders')
    def test_folder_list_not_root(self, mock_drive_client_folders):
        mock_drive_client_folders.return_value = sample_folder_data['items']
        folderId = '12345'
        self.node_settings.set_auth(external_account=self.external_account, user=self.user)
        self.node_settings.save()

        url = self.project.api_url_for('iqbrims_folder_list', folder_id=folderId)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), len(sample_folder_data['items']))

    @mock.patch.object(IQBRIMSClient, 'about')
    def test_folder_list(self, mock_about):
        mock_about.return_value = {'rootFolderId': '24601'}
        super(TestConfigViews, self).test_folder_list()

class TestStatusViews(IQBRIMSAddonTestCase, OsfTestCase):

    def setUp(self):
        super(TestStatusViews, self).setUp()
        self.mock_about = mock.patch.object(
            IQBRIMSClient,
            'about'
        )
        self.mock_about.return_value = {'rootFolderId': '24601'}
        self.mock_about.start()
        self.mock_get_folder_info = mock.patch.object(
            IQBRIMSClient,
            'get_folder_info'
        )
        self.mock_get_folder_info.return_value = {'title': 'Test-xxxxx'}
        self.mock_get_folder_info.start()
        self.mock_rename_folder = mock.patch.object(
            IQBRIMSClient,
            'rename_folder'
        )
        self.mock_rename_folder.start()
        self.mock_fetch = mock.patch.object(
            self.node_settings.__class__,
            'fetch_access_token'
        )
        self.mock_fetch.return_value = self.external_account.oauth_key
        self.mock_fetch.start()

    def tearDown(self):
        self.mock_about.stop()
        self.mock_get_folder_info.stop()
        self.mock_rename_folder.stop()
        self.mock_fetch.stop()
        super(TestStatusViews, self).tearDown()

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_get_status(self, mock_get_management_node):
        mock_get_management_node.return_value = mock.MagicMock(_id='fake_management_node_id')

        url = self.project.api_url_for('iqbrims_get_status')
        res = self.app.get(url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_items_equal(res.json.keys(), ['data'])
        assert_items_equal(res.json['data'].keys(), ['id', 'type', 'attributes'])
        assert_equal(res.json['data']['id'], self.project._id)
        assert_equal(res.json['data']['type'], 'iqbrims-status')
        assert_items_equal(res.json['data']['attributes'].keys(), ['state', 'labo_list', 'review_folders', 'is_admin'])
        assert_equal(res.json['data']['attributes']['state'], 'initialized')
        assert_equal(len(res.json['data']['attributes']['labo_list']), len(settings.LABO_LIST))
        assert_equal(res.json['data']['attributes']['review_folders'], iqbrims_views.REVIEW_FOLDERS)
        assert_equal(res.json['data']['attributes']['is_admin'], False)

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_get_status_with_admin(self, mock_get_management_node):
        mock_get_management_node.return_value = mock.MagicMock(_id=self.project._id)

        url = self.project.api_url_for('iqbrims_get_status')
        res = self.app.get(url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_items_equal(res.json.keys(), ['data'])
        assert_items_equal(res.json['data'].keys(), ['id', 'type', 'attributes'])
        assert_equal(res.json['data']['id'], self.project._id)
        assert_equal(res.json['data']['type'], 'iqbrims-status')
        assert_items_equal(res.json['data']['attributes'].keys(), ['state', 'labo_list', 'review_folders', 'is_admin',
                                                                   'task_url'])
        assert_equal(res.json['data']['attributes']['state'], 'initialized')
        assert_equal(len(res.json['data']['attributes']['labo_list']), len(settings.LABO_LIST))
        assert_equal(res.json['data']['attributes']['review_folders'], iqbrims_views.REVIEW_FOLDERS)
        assert_equal(res.json['data']['attributes']['is_admin'], True)
        assert_equal(res.json['data']['attributes']['task_url'], settings.FLOWABLE_TASK_URL)

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_get_status_with_other_state(self, mock_get_management_node):
        state = 'check'
        mock_get_management_node.return_value = mock.MagicMock(_id='fake_management_node_id')
        self.project.get_addon('iqbrims').status = state

        url = self.project.api_url_for('iqbrims_get_status')
        res = self.app.get(url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_in('data', res.json)
        assert_in('attributes', res.json['data'])
        assert_in('state', res.json['data']['attributes'])
        assert_equal(res.json['data']['attributes']['state'], 'initialized')

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_set_status(self, mock_get_management_node):
        status = {
            'state': 'fake_state',
            'other_attribute': 'fake_other_attribute'
        }
        mock_get_management_node.return_value = mock.MagicMock(_id=self.project._id)

        url = self.project.api_url_for('iqbrims_set_status')
        payload = {
            'data': {
                'attributes': status
            }
        }
        res = self.app.patch_json(url, params=payload, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {
            'data': {
                'attributes': status,
                'type': 'iqbrims-status',
                'id': self.project._id
            }
        })

    @mock.patch.object(IQBRIMSFlowableClient, 'start_workflow')
    @mock.patch.object(iqbrims_views, '_iqbrims_update_spreadsheet')
    @mock.patch.object(iqbrims_views, '_iqbrims_init_folders')
    @mock.patch.object(iqbrims_views, '_iqbrims_import_auth_from_management_node')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_set_status_to_deposit(self, mock_get_management_node, mock_import_auth_from_management_node,
                                   mock_iqbrims_init_folders, mock_update_spreadsheet,
                                   mock_flowable_start_workflow):
        status = {
            'state': 'deposit',
            'labo_id': 'fake_labo_name',
            'other_attribute': 'fake_other_attribute'
        }
        fake_folder = {
            'id': '382635482',
            'path': 'fake/folder/path'
        }
        fake_management_project = ProjectFactory(creator=self.user)
        mock_get_management_node.return_value = fake_management_project
        mock_import_auth_from_management_node.return_value = None
        mock_iqbrims_init_folders.return_value = fake_folder
        mock_update_spreadsheet.return_value = None
        mock_flowable_start_workflow.return_value = None

        url = self.project.api_url_for('iqbrims_set_status')
        payload = {
            'data': {
                'attributes': status
            }
        }
        res = self.app.patch_json(url, params=payload, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {
            'data': {
                'attributes': status,
                'type': 'iqbrims-status',
                'id': self.project._id
            }
        })

        iqbrims = self.project.get_addon('iqbrims')
        secret = iqbrims.get_secret()
        assert_is_not_none(secret)
        assert_equal(iqbrims.folder_id, fake_folder['id'])
        assert_equal(iqbrims.folder_path, fake_folder['path'])

        assert_equal(mock_import_auth_from_management_node.call_count, 1)
        assert_items_equal(mock_import_auth_from_management_node.call_args[0], [
            self.project,
            iqbrims,
            fake_management_project
        ])

        assert_equal(mock_iqbrims_init_folders.call_count, 1)
        assert_items_equal(mock_iqbrims_init_folders.call_args[0], [
            self.project,
            fake_management_project,
            status['state'],
            status['labo_id']
        ])

        assert_equal(mock_update_spreadsheet.call_count, 1)
        assert_items_equal(mock_update_spreadsheet.call_args[0], [
            self.project,
            fake_management_project,
            status['state'],
            payload['data']['attributes']
        ])

        assert_equal(mock_flowable_start_workflow.call_count, 1)
        assert_items_equal(mock_flowable_start_workflow.call_args[0], [
            self.project._id,
            self.project.title,
            payload['data']['attributes'],
            secret
        ])

    @mock.patch.object(IQBRIMSFlowableClient, 'start_workflow')
    @mock.patch.object(iqbrims_views, '_iqbrims_update_spreadsheet')
    @mock.patch.object(iqbrims_views, '_iqbrims_init_folders')
    @mock.patch.object(iqbrims_views, '_iqbrims_import_auth_from_management_node')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_set_status_to_check(self, mock_get_management_node, mock_import_auth_from_management_node,
                                 mock_iqbrims_init_folders, mock_update_spreadsheet,
                                 mock_flowable_start_workflow):
        status = {
            'state': 'check',
            'labo_id': 'fake_labo_name',
            'other_attribute': 'fake_other_attribute'
        }
        fake_folder = {
            'id': '382635482',
            'path': 'fake/folder/path'
        }
        fake_management_project = ProjectFactory(creator=self.user)
        mock_get_management_node.return_value = fake_management_project
        mock_import_auth_from_management_node.return_value = None
        mock_iqbrims_init_folders.return_value = fake_folder
        mock_update_spreadsheet.return_value = None
        mock_flowable_start_workflow.return_value = None

        url = self.project.api_url_for('iqbrims_set_status')
        payload = {
            'data': {
                'attributes': status
            }
        }
        res = self.app.patch_json(url, params=payload, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {
            'data': {
                'attributes': status,
                'type': 'iqbrims-status',
                'id': self.project._id
            }
        })

        iqbrims = self.project.get_addon('iqbrims')
        secret = iqbrims.get_secret()
        assert_is_not_none(secret)
        assert_equal(iqbrims.folder_id, fake_folder['id'])
        assert_equal(iqbrims.folder_path, fake_folder['path'])

        assert_equal(mock_import_auth_from_management_node.call_count, 1)
        assert_items_equal(mock_import_auth_from_management_node.call_args[0], [
            self.project,
            iqbrims,
            fake_management_project
        ])

        assert_equal(mock_iqbrims_init_folders.call_count, 1)
        assert_items_equal(mock_iqbrims_init_folders.call_args[0], [
            self.project,
            fake_management_project,
            status['state'],
            status['labo_id']
        ])

        assert_equal(mock_update_spreadsheet.call_count, 1)
        assert_items_equal(mock_update_spreadsheet.call_args[0], [
            self.project,
            fake_management_project,
            status['state'],
            payload['data']['attributes']
        ])

        assert_equal(mock_flowable_start_workflow.call_count, 1)
        assert_items_equal(mock_flowable_start_workflow.call_args[0], [
            self.project._id,
            self.project.title,
            payload['data']['attributes'],
            secret
        ])


class TestStorageViews(IQBRIMSAddonTestCase, OsfTestCase):

    def setUp(self):
        super(TestStorageViews, self).setUp()
        self.mock_about = mock.patch.object(
            IQBRIMSClient,
            'about'
        )
        self.mock_about.return_value = {'rootFolderId': '24601'}
        self.mock_about.start()
        self.mock_get_folder_info = mock.patch.object(
            IQBRIMSClient,
            'get_folder_info'
        )
        self.mock_get_folder_info.return_value = {'title': 'Test-xxxxx'}
        self.mock_get_folder_info.start()
        self.mock_fetch = mock.patch.object(
            self.node_settings.__class__,
            'fetch_access_token'
        )
        self.mock_fetch.return_value = self.external_account.oauth_key
        self.mock_fetch.start()

    def tearDown(self):
        self.mock_about.stop()
        self.mock_get_folder_info.stop()
        self.mock_fetch.stop()
        super(TestStorageViews, self).tearDown()

    def test_unauthorized_reject_storage(self):
        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()

        url = self.project.api_url_for('iqbrims_reject_storage',
                                       folder='paper')
        res = self.app.delete(url,
                              expect_errors=True).maybe_follow()

        assert_equal(res.status_code, 403)

        url = self.project.api_url_for('iqbrims_reject_storage',
                                       folder='paper')
        res = self.app.delete(url, headers={'X-RDM-Token': 'invalid123'},
                              expect_errors=True).maybe_follow()

        assert_equal(res.status_code, 403)

    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'create_folder')
    @mock.patch.object(IQBRIMSClient, 'rename_folder')
    @mock.patch.object(IQBRIMSClient, 'folders')
    def test_reject_checklist_storage(self, mock_folders, mock_rename_folder,
                                      mock_create_folder,
                                      mock_get_management_node):
        management_project = ProjectFactory()
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'rmfolderid123',
                                      'title': u'チェックリスト'}]

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_reject_storage',
                                       folder='checklist')
        res = self.app.delete(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'rejected',
                                'root_folder': 'iqb123/'})
        mock_rename_folder.assert_called_once()
        cargs, _ = mock_rename_folder.call_args
        assert_equal(cargs[0], 'rmfolderid123')
        assert_true(re.match(r'(.*)\.[0-9]+\-[0-9]+',
                             cargs[1]).group(1) == u'チェックリスト')
        mock_create_folder.assert_called_once()
        assert_equal(mock_create_folder.call_args,
                     (('1234567890', u'チェックリスト'),))

    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'delete_file')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    def test_reject_scan_storage(self, mock_files, mock_folders,
                                 mock_delete_file, mock_get_management_node):
        management_project = ProjectFactory()
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'rmfolderid123',
                                      'title': u'スキャン結果'}]
        mock_files.return_value = [{'id': 'rmfileid123', 'title': 'scan.pdf'}]

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_reject_storage',
                                       folder='scan')
        res = self.app.delete(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'rejected',
                                'root_folder': 'iqb123/'})
        mock_delete_file.assert_called_once()
        assert_equal(mock_delete_file.call_args, (('rmfileid123',),))

    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    def test_create_index_in_progress(self, mock_files, mock_folders,
                                      mock_get_management_node):
        management_project = ProjectFactory()
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'rmfolderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = []

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_create_index',
                                       folder='scan')
        res = self.app.put(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'processing'})

    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'get_content')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    @mock.patch.object(IQBRIMSClient, 'create_spreadsheet')
    @mock.patch.object(SpreadsheetClient, 'sheets')
    @mock.patch.object(SpreadsheetClient, 'add_files')
    @mock.patch.object(IQBRIMSClient, 'grant_access_from_anyone')
    @mock.patch.object(IQBRIMSClient, 'get_file_link')
    def test_create_index(self, mock_get_file_link,
                          mock_grant_access_from_anyone, mock_add_files,
                          mock_sheets, mock_create_spreadsheet,
                          mock_files, mock_folders, mock_get_content,
                          mock_get_management_node):
        management_project = ProjectFactory()
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        mock_get_content.return_value = b'f1.txt\nf2.txt\ntest/file3.txt\n'
        mock_folders.return_value = [{'id': 'rmfolderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = [{'id': 'fileid123', 'title': 'files.txt'}]
        mock_create_spreadsheet.return_value = {'id': 'sheet123'}
        mock_sheets.return_value = [{'properties': {'title': 'Files',
                                                    'sheetId': 'ss123'}}]
        mock_grant_access_from_anyone.return_value = {}
        mock_get_file_link.return_value = 'https://a.b/sheet123'

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_create_index',
                                       folder='scan')
        res = self.app.put(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete',
                                'url': 'https://a.b/sheet123'})
        mock_get_content.assert_called_once()
        assert_equal(mock_get_content.call_args, (('fileid123',),))
        mock_grant_access_from_anyone.assert_called_once()
        assert_equal(mock_grant_access_from_anyone.call_args,
                     (('sheet123',),))
        mock_add_files.assert_called_once()
        assert_equal(mock_add_files.call_args,
                     (('Files', 'ss123',
                       ['f1.txt', 'f2.txt', 'test/file3.txt', '']),))

    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'get_content')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    @mock.patch.object(IQBRIMSClient, 'create_spreadsheet')
    @mock.patch.object(SpreadsheetClient, 'sheets')
    @mock.patch.object(SpreadsheetClient, 'add_files')
    @mock.patch.object(IQBRIMSClient, 'grant_access_from_anyone')
    @mock.patch.object(IQBRIMSClient, 'get_file_link')
    def test_create_index_ja(self, mock_get_file_link,
                             mock_grant_access_from_anyone, mock_add_files,
                             mock_sheets, mock_create_spreadsheet,
                             mock_files, mock_folders, mock_get_content,
                             mock_get_management_node):
        management_project = ProjectFactory()
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        mock_get_content.return_value = u'f1.txt\nf2.txt\ntest/ファイル3.txt\n'.encode('utf8')
        mock_folders.return_value = [{'id': 'rmfolderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = [{'id': 'fileid123', 'title': 'files.txt'}]
        mock_create_spreadsheet.return_value = {'id': 'sheet123'}
        mock_sheets.return_value = [{'properties': {'title': 'Files',
                                                    'sheetId': 'ss123'}}]
        mock_grant_access_from_anyone.return_value = {}
        mock_get_file_link.return_value = 'https://a.b/sheet123'

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_create_index',
                                       folder='scan')
        res = self.app.put(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete',
                                'url': 'https://a.b/sheet123'})
        mock_get_content.assert_called_once()
        assert_equal(mock_get_content.call_args, (('fileid123',),))
        mock_grant_access_from_anyone.assert_called_once()
        assert_equal(mock_grant_access_from_anyone.call_args,
                     (('sheet123',),))
        mock_add_files.assert_called_once()
        assert_equal(mock_add_files.call_args,
                     (('Files', 'ss123',
                       ['f1.txt', 'f2.txt', u'test/ファイル3.txt', '']),))


class TestNotificationViews(IQBRIMSAddonTestCase, OsfTestCase):

    def setUp(self):
        super(TestNotificationViews, self).setUp()
        self.mock_about = mock.patch.object(
            IQBRIMSClient,
            'about'
        )
        self.mock_about.return_value = {'rootFolderId': '24601'}
        self.mock_about.start()
        self.mock_get_folder_info = mock.patch.object(
            IQBRIMSClient,
            'get_folder_info'
        )
        self.mock_get_folder_info.return_value = {'title': 'Test-xxxxx'}
        self.mock_get_folder_info.start()
        self.mock_rename_folder = mock.patch.object(
            IQBRIMSClient,
            'rename_folder'
        )
        self.mock_rename_folder.start()
        self.mock_fetch = mock.patch.object(
            self.node_settings.__class__,
            'fetch_access_token'
        )
        self.mock_fetch.return_value = self.external_account.oauth_key
        self.mock_fetch.start()

    def tearDown(self):
        self.mock_about.stop()
        self.mock_get_folder_info.stop()
        self.mock_rename_folder.stop()
        self.mock_fetch.stop()
        super(TestNotificationViews, self).tearDown()

    def test_unauthorized_post_notify(self):
        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()

        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post(url,
                            expect_errors=True).maybe_follow()

        assert_equal(res.status_code, 403)

        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post(url, headers={'X-RDM-Token': 'invalid123'},
                            expect_errors=True).maybe_follow()

        assert_equal(res.status_code, 403)

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_jpn_without_mail(self, mock_get_management_node):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['admin', 'user'],
          'notify_title': u'日本語',
          'notify_body': u'日本語'
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_items_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 3)
        assert_equal(management_project.logs.count(), 2)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 1)
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 1)

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_without_mail(self, mock_get_management_node,
                                      mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['admin', 'user']
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_items_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 3)
        assert_equal(management_project.logs.count(), 2)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 1)
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 1)
        assert mock_send_mail.call_args is None

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_user_without_mail(self, mock_get_management_node,
                                           mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['user']
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_items_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 3)
        assert_equal(management_project.logs.count(), 1)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 1)
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 0)
        assert mock_send_mail.call_args is None

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_adm_without_mail(self, mock_get_management_node,
                                          mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['admin']
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_items_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 2)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 0)
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 1)
        assert mock_send_mail.call_args is None

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_with_mail(self, mock_get_management_node,
                                   mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['admin', 'user'],
          'use_mail': True,
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_items_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 3)
        assert_equal(management_project.logs.count(), 2)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 1)
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 1)
        assert mock_send_mail.call_args is not None

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_body(self, mock_get_management_node, mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        body_html = u'''こんにちは。<br>
連絡です。<br>

URL: <a href="http://test.test">http://test.test</a><br>
文末。
'''
        comment_html = u'''**iqbrims_test_notify** こんにちは。<br>
連絡です。<br>

URL: http://test.test<br>
文末。
'''
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['admin', 'user'],
          'notify_body': body_html,
          'use_mail': True,
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_items_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 3)
        assert_equal(management_project.logs.count(), 2)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 1)
        assert user_comments.get().content == comment_html
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 1)
        assert admin_comments.get().content == comment_html
        assert mock_send_mail.call_args is not None
