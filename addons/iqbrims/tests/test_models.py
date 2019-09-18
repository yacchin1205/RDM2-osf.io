# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa (PEP8 asserts)
import pytest
import unittest

from framework.auth import Auth
from addons.base.tests.models import (OAuthAddonNodeSettingsTestSuiteMixin,
                                      OAuthAddonUserSettingTestSuiteMixin)

from addons.iqbrims import settings
from addons.iqbrims.models import NodeSettings, IQBRIMSProvider
from addons.iqbrims.client import IQBRIMSClient, IQBRIMSAuthClient, SpreadsheetClient
from addons.iqbrims.tests.factories import (
    IQBRIMSAccountFactory,
    IQBRIMSNodeSettingsFactory,
    IQBRIMSUserSettingsFactory
)
import addons.iqbrims.models as iqbrims_models
from addons.iqbrims.utils import get_folder_title
from osf.models import RdmAddonOption
from osf_tests.factories import ProjectFactory, InstitutionFactory

pytestmark = pytest.mark.django_db

class TestIQBRIMSProvider(unittest.TestCase):
    def setUp(self):
        super(TestIQBRIMSProvider, self).setUp()
        self.provider = IQBRIMSProvider()

    @mock.patch.object(IQBRIMSAuthClient, 'userinfo')
    def test_handle_callback(self, mock_client):
        fake_response = {'access_token': 'abc123'}
        fake_info = {'sub': '12345', 'name': 'fakename', 'profile': 'fakeUrl'}
        mock_client.return_value = fake_info
        res = self.provider.handle_callback(fake_response)
        assert_equal(res['provider_id'], '12345')
        assert_equal(res['display_name'], 'fakename')
        assert_equal(res['profile_url'], 'fakeUrl')

class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 'iqbrims'
    full_name = 'IQB-RIMS'
    ExternalAccountFactory = IQBRIMSAccountFactory

    def setUp(self):
        super(TestUserSettings, self).setUp()
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

    def tearDown(self):
        self.mock_get_folder_info.stop()
        self.mock_rename_folder.stop()
        super(TestUserSettings, self).tearDown()


class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    short_name = 'iqbrims'
    full_name = 'IQB-RIMS'
    ExternalAccountFactory = IQBRIMSAccountFactory

    NodeSettingsFactory = IQBRIMSNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = IQBRIMSUserSettingsFactory

    def setUp(self):
        self.mock_refresh = mock.patch.object(
            IQBRIMSProvider,
            'refresh_oauth_key'
        )
        self.mock_refresh.return_value = True
        self.mock_refresh.start()
        super(TestNodeSettings, self).setUp()
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

    def tearDown(self):
        self.mock_refresh.stop()
        self.mock_get_folder_info.stop()
        self.mock_rename_folder.stop()
        super(TestNodeSettings, self).tearDown()

    @mock.patch('addons.iqbrims.models.IQBRIMSProvider')
    def test_api_not_cached(self, mock_gdp):
        # The first call to .api returns a new object
        api = self.node_settings.api
        mock_gdp.assert_called_once()
        assert_equal(api, mock_gdp())

    @mock.patch('addons.iqbrims.models.IQBRIMSProvider')
    def test_api_cached(self, mock_gdp):
        # Repeated calls to .api returns the same object
        self.node_settings._api = 'testapi'
        api = self.node_settings.api
        assert_false(mock_gdp.called)
        assert_equal(api, 'testapi')

    def test_selected_folder_name_root(self):
        self.node_settings.folder_id = 'root'

        assert_equal(
            self.node_settings.selected_folder_name,
            'Full IQB-RIMS'
        )

    def test_selected_folder_name_empty(self):
        self.node_settings.folder_id = None

        assert_equal(
            self.node_settings.selected_folder_name,
            ''
        )

    ## Overrides ##

    def test_set_folder(self):
        folder = {
            'id': 'fake-folder-id',
            'name': 'fake-folder-name',
            'path': 'fake_path'
        }
        self.node_settings.set_folder(folder, auth=Auth(self.user))
        self.node_settings.save()
        # Folder was set
        assert_equal(self.node_settings.folder_id, folder['id'])
        # Log was saved
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, '{0}_folder_selected'.format(self.short_name))

    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {
            'folder':
            {
                'id': self.node_settings.folder_id,
                'name': self.node_settings.folder_name,
                'path': self.node_settings.folder_path,
            },
            'permissions':
            {
                u'チェックリスト': ['VISIBLE', 'WRITABLE'],
                u'スキャン結果': [],
                u'生データ': ['VISIBLE', 'WRITABLE'],
                u'最終原稿・組図': ['VISIBLE', 'WRITABLE']
            }
        }
        assert_equal(settings, expected)


class TestIQBRIMSNodeReceiverUpdateFolderName(unittest.TestCase):

    short_name = 'iqbrims'
    full_name = 'IQB-RIMS'
    folder_id = '1234567890'

    def setUp(self):
        super(TestIQBRIMSNodeReceiverUpdateFolderName, self).setUp()
        self.node = ProjectFactory()
        self.user = self.node.creator
        self.external_account = IQBRIMSAccountFactory()

        self.user.external_accounts.add(self.external_account)
        self.user.save()

        self.user_settings = self.user.add_addon(self.short_name)
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': self.folder_id}
        )
        self.user_settings.save()

        self.node_settings = IQBRIMSNodeSettingsFactory(
            external_account=self.external_account,
            user_settings=self.user_settings,
            folder_id=self.folder_id,
            owner=self.node
        )

        self.institution = InstitutionFactory()

    @mock.patch.object(NodeSettings, 'fetch_access_token')
    @mock.patch.object(IQBRIMSClient, 'rename_folder')
    @mock.patch.object(IQBRIMSClient, 'get_folder_info')
    def test_update_folder_name(self, mock_get_folder_info, mock_rename_folder, mock_fetch_access_token):
        mock_get_folder_info.return_value = {'title': 'dummy_folder_title'}
        mock_fetch_access_token.return_value = 'dummy_token'
        mock_rename_folder.return_value = None
        new_folder_title = get_folder_title(self.node)

        self.node.save(force_update=True)

        assert_equal(mock_get_folder_info.call_count, 1)
        assert_items_equal(mock_get_folder_info.call_args, ((), {'folder_id': self.folder_id}))

        assert_equal(mock_rename_folder.call_count, 1)
        assert_items_equal(mock_rename_folder.call_args[0], (self.folder_id, new_folder_title))


class TestIQBRIMSNodeReceiverUpdateSpreadsheet(unittest.TestCase):

    short_name = 'iqbrims'
    full_name = 'IQB-RIMS'
    folder_id = '1234567890'
    management_folder_id = 'management_1234567890'

    def setUp(self):
        super(TestIQBRIMSNodeReceiverUpdateSpreadsheet, self).setUp()
        self.institution = InstitutionFactory()

        self.node = ProjectFactory()
        self.user = self.node.creator
        self.external_account = IQBRIMSAccountFactory()
        self.user.external_accounts.add(self.external_account)
        self.user.save()
        self.user.affiliated_institutions.add(self.institution)
        self.node.affiliated_institutions.add(self.institution)
        self.user_settings = self.user.add_addon(self.short_name)
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': self.folder_id}
        )
        self.user_settings.save()
        self.node_settings = IQBRIMSNodeSettingsFactory(
            external_account=self.external_account,
            user_settings=self.user_settings,
            folder_id=self.folder_id,
            owner=self.node
        )

        self.management_node = ProjectFactory()
        self.management_user = self.management_node.creator
        self.management_external_account = IQBRIMSAccountFactory()
        self.management_user.affiliated_institutions.add(self.institution)
        self.management_node.affiliated_institutions.add(self.institution)
        self.management_user.external_accounts.add(self.management_external_account)
        self.management_user.save()
        self.management_user_settings = self.management_user.add_addon(self.short_name)
        self.management_user_settings.grant_oauth_access(
            node=self.management_node,
            external_account=self.management_external_account,
            metadata={'folder': self.management_folder_id}
        )
        self.management_user_settings.save()
        self.management_node_settings = IQBRIMSNodeSettingsFactory(
            external_account=self.management_external_account,
            user_settings=self.management_user_settings,
            folder_id=self.management_folder_id,
            owner=self.management_node
        )

        self.rdm_addon_option = RdmAddonOption(
            provider=self.short_name,
            institution=self.institution,
            management_node=self.management_node
        ).save()

        # disable update_folder_name receiver
        self.mock_get_folder_info = mock.patch.object(
            IQBRIMSClient,
            'get_folder_info',
            return_value={'title': 'dummy_folder_name'}
        )
        self.mock_get_folder_info.start()
        self.mock_rename_folder = mock.patch.object(
            IQBRIMSClient,
            'rename_folder'
        )
        self.mock_rename_folder.start()

        self.mock_fetch_access_token = mock.patch.object(
            NodeSettings,
            'fetch_access_token',
            return_value='fake_token'
        )
        self.mock_fetch_access_token.start()

        mock_rootr = {'id': 'fake_rootr_id'}
        self.mock_create_folder_if_not_exists = mock.patch.object(
            IQBRIMSClient,
            'create_folder_if_not_exists',
            return_value=(False, mock_rootr)
        )
        self.mock_create_folder_if_not_exists.start()

        mock_r = {'id': 'fake_r_id'}
        self.mock_create_spreadsheet_if_not_exists = mock.patch.object(
            IQBRIMSClient,
            'create_spreadsheet_if_not_exists',
            return_value=(False, mock_r)
        )
        self.mock_create_spreadsheet_if_not_exists.start()

        self.mock_add_sheet = mock.patch.object(
            SpreadsheetClient,
            'add_sheet'
        )
        self.mock_add_sheet.start()

        mock_sheet = {
            'properties': {
                'title': settings.APPSHEET_SHEET_NAME,
                'gridProperties': {
                    'rowCount': 100
                }
            }
        }
        self.mock_sheets = mock.patch.object(
            SpreadsheetClient,
            'sheets',
            return_value=[mock_sheet])
        self.mock_sheets.start()

        self.mock_get_folder_link = mock.patch.object(
            IQBRIMSClient,
            'get_folder_link',
            return_value='fake_link')
        self.mock_get_folder_link.start()

        self.mock_get_row = mock.patch.object(
            SpreadsheetClient,
            'get_row',
            return_value=[])
        self.mock_get_row.start()

    def tearDown(self):
        super(TestIQBRIMSNodeReceiverUpdateSpreadsheet, self).tearDown()
        self.mock_get_folder_info.stop()
        self.mock_rename_folder.stop()
        self.mock_fetch_access_token.stop()
        self.mock_create_folder_if_not_exists.stop()
        self.mock_create_spreadsheet_if_not_exists.stop()
        self.mock_add_sheet.stop()
        self.mock_sheets.stop()
        self.mock_get_folder_link.stop()

    @mock.patch.object(SpreadsheetClient, 'ensure_columns')
    @mock.patch.object(SpreadsheetClient, 'get_row_values')
    @mock.patch.object(SpreadsheetClient, 'update_row')
    def test_update_node_check(self, mock_update_row, mock_get_row_values, mock_ensure_columns):
        mock_get_row_values.return_value = [
            'dummy_node_id1',
            'dummy_node_id2',
            self.node._id,
            'dummy_node_id3',
        ]
        mock_ensure_columns.return_value = [
            u'Project ID',
            'Title',
            'Current Status',
        ]
        self.node_settings.set_status({
            'state': 'check',
            'labo_id': settings.LABO_LIST[0]['id'],
            'workflow_overall_state': 'fake_workflow_state',
        })

        self.node.save(force_update=True)

        mock_update_row.assert_called_once()
        cargs, _ = mock_update_row.call_args
        sheet_id, values, update_at = cargs
        self.assertEqual(sheet_id, settings.APPSHEET_SHEET_NAME)
        self.assertEqual(values, [
            self.node._id,
            self.node.title,
            'fake_workflow_state'
        ])
        self.assertEqual(update_at, 2)

    @mock.patch.object(SpreadsheetClient, 'ensure_columns')
    @mock.patch.object(SpreadsheetClient, 'get_row_values')
    @mock.patch.object(SpreadsheetClient, 'update_row')
    def test_update_node_deposit(self, mock_update_row, mock_get_row_values, mock_ensure_columns):
        mock_get_row_values.return_value = [
            'dummy_node_id1',
            self.node._id,
            'dummy_node_id2',
            'dummy_node_id3',
        ]
        mock_ensure_columns.return_value = [
            u'Project ID',
            'Title',
            'Current Status',
        ]
        self.node_settings.set_status({
            'state': 'deposit',
            'labo_id': settings.LABO_LIST[0]['id'],
            'workflow_overall_state': 'fake_workflow_state',
        })

        self.node.save(force_update=True)

        mock_update_row.assert_called_once()
        cargs, _ = mock_update_row.call_args
        sheet_id, values, update_at = cargs
        self.assertEqual(sheet_id, settings.APPSHEET_SHEET_NAME)
        self.assertEqual(values, [
            self.node._id,
            self.node.title,
            'fake_workflow_state'
        ])
        self.assertEqual(update_at, 1)

    @mock.patch.object(iqbrims_models, 'get_management_node')
    @mock.patch.object(iqbrims_models, 'iqbrims_update_spreadsheet')
    def test_update_no_state_node(self, mock_update_spreadsheet, mock_get_management_node):
        mock_get_management_node.return_value = mock.MagicMock(_id='management_id')
        self.node.save(force_update=True)
        assert_equal(mock_update_spreadsheet.call_count, 0)

    @mock.patch.object(iqbrims_models, 'get_management_node')
    @mock.patch.object(iqbrims_models, 'iqbrims_update_spreadsheet')
    def test_update_management_node(self, mock_update_spreadsheet, mock_get_management_node):
        mock_get_management_node.return_value = self.node
        self.node.save(force_update=True)
        assert_equal(mock_update_spreadsheet.call_count, 0)
