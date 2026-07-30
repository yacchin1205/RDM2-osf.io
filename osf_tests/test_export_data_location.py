from unittest import mock
import pytest
from django.test import TestCase

from osf_tests.factories import ExportDataLocationFactory


class FakeAddon:
    short_name = 'glowcloud'
    full_name = 'Own cloud'


@pytest.mark.feature_202210
@pytest.mark.django_db
class TestExportDataRestore(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.export_data_location = ExportDataLocationFactory()
        cls.addon = FakeAddon()

    def test_repr(self):
        expect_value = '"{}/{}"'.format(self.export_data_location.institution_guid, self.export_data_location.name)
        assert (repr(self.export_data_location)) == (expect_value)

    def test_str(self):
        expect_value = '"{}/{}"'.format(self.export_data_location.institution_guid, self.export_data_location.name)
        assert (str(self.export_data_location)) == (expect_value)

    def test_unicode(self):
        expect_value = '{}'.format(self.export_data_location.name)
        assert (self.export_data_location.__unicode__()) == (expect_value)

    def test_provider_name(self):
        expect_value = self.export_data_location.waterbutler_settings['storage']['provider']
        assert (self.export_data_location.provider_name) == (expect_value)

    def test_addon_not_null(self):
        expect_value = self.export_data_location.waterbutler_settings['storage']['provider']
        mock_settings = mock.MagicMock()
        mock_settings.ADDONS_AVAILABLE = [self.addon]
        with mock.patch('osf.models.export_data_location.website_settings', mock_settings):
            res = self.export_data_location.addon
            assert (res.short_name) == (expect_value)

    def test_addon_null(self):
        mock_website_settings = mock.MagicMock()
        mock_website_settings.ADDONS_AVAILABLE = []
        with mock.patch('osf.models.export_data_location.website_settings', mock_website_settings):
            res = self.export_data_location.addon
            assert (res) == (None)

    def test_provider_short_name_not_null(self):
        expect_value = self.addon.short_name
        mock_website_settings = mock.MagicMock()
        mock_website_settings.ADDONS_AVAILABLE = [self.addon]
        with mock.patch('osf.models.export_data_location.website_settings', mock_website_settings):
            res = self.export_data_location.provider_short_name
            assert (res) == (expect_value)

    def test_provider_short_name_null(self):
        mock_website_settings = mock.MagicMock()
        mock_website_settings.ADDONS_AVAILABLE = []
        with mock.patch('osf.models.export_data_location.website_settings', mock_website_settings):
            res = self.export_data_location.provider_short_name
            assert (res) == (None)

    def test_provider_full_name_not_null(self):
        expect_value = self.addon.full_name
        mock_website_settings = mock.MagicMock()
        mock_website_settings.ADDONS_AVAILABLE = [self.addon]
        with mock.patch('osf.models.export_data_location.website_settings', mock_website_settings):
            res = self.export_data_location.provider_full_name
            assert (res) == (expect_value)

    def test_provider_full_name_null(self):
        mock_website_settings = mock.MagicMock()
        mock_website_settings.ADDONS_AVAILABLE = []
        with mock.patch('osf.models.export_data_location.website_settings', mock_website_settings):
            res = self.export_data_location.provider_full_name
            assert (res) == (None)

    def test_serialize_waterbutler_credentials_s3(self):
        res = self.export_data_location.serialize_waterbutler_credentials('s3')
        expect_value = dict(self.export_data_location.waterbutler_credentials['storage']).copy()
        assert (res['secret_key']) == (expect_value['secret_key'])

    def test_serialize_waterbutler_credentials_s3compat(self):
        res = self.export_data_location.serialize_waterbutler_credentials('s3compat')
        expect_value = dict(self.export_data_location.waterbutler_credentials['storage']).copy()
        assert (res['secret_key']) == (expect_value['secret_key'])

    def test_serialize_waterbutler_credentials_s3compatsigv4(self):
        res = self.export_data_location.serialize_waterbutler_credentials('s3compatsigv4')
        expect_value = dict(self.export_data_location.waterbutler_credentials['storage']).copy()
        assert (res['secret_key']) == (expect_value['secret_key'])

    def test_serialize_waterbutler_credentials_nextcloudinstitutions(self):
        res = self.export_data_location.serialize_waterbutler_credentials('nextcloudinstitutions')
        assert (res['host']) == (self.export_data_location.waterbutler_credentials['external_account']['oauth_secret'])

    def test_serialize_waterbutler_credentials_dropboxbusiness(self):
        res = self.export_data_location.serialize_waterbutler_credentials('dropboxbusiness')
        assert (res['token']) == (self.export_data_location.waterbutler_credentials['external_account']['fileaccess_token'])

    def test_serialize_waterbutler_settings_s3(self):
        res = self.export_data_location.serialize_waterbutler_settings('s3')
        assert (res['bucket']) == (self.export_data_location.waterbutler_settings['storage']['bucket'])

    def test_serialize_waterbutler_settings_s3compat(self):
        res = self.export_data_location.serialize_waterbutler_settings('s3compat')
        assert (res['bucket']) == (self.export_data_location.waterbutler_settings['storage']['bucket'])

    def test_serialize_waterbutler_settings_s3compatsigv4(self):
        res = self.export_data_location.serialize_waterbutler_settings('s3compatsigv4')
        assert (res['bucket']) == (self.export_data_location.waterbutler_settings['storage']['bucket'])

    def test_serialize_waterbutler_settings_nextcloudinstitutions(self):
        res = self.export_data_location.serialize_waterbutler_settings('nextcloudinstitutions')
        assert (res) != (None)

    def test_serialize_waterbutler_settings_dropboxbusiness(self):
        res = self.export_data_location.serialize_waterbutler_settings('dropboxbusiness')
        assert (res['admin_dbmid']) == (self.export_data_location.waterbutler_settings['admin_dbmid'])
        assert (res['team_folder_id']) == (self.export_data_location.waterbutler_settings['team_folder_id'])
