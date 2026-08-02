from django.test import RequestFactory
from rest_framework import status as http_status
import json
from unittest import mock
from swiftclient import exceptions as swift_exceptions

from addons.osfstorage.models import Region
from admin.rdm_custom_storage_location import views
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
)
from tests.base import AdminTestCase


class TestConnection(AdminTestCase):

    def setUp(self):
        super(TestConnection, self).setUp()
        self.mock_can_list = mock.patch('addons.swift.views.utils.can_list')
        self.mock_can_list.return_value = True
        self.mock_can_list.start()

        self.mock_uid = mock.patch('addons.swift.views.utils.get_user_info')
        self.mock_uid.return_value = {'id': '1234567890', 'display_name': 'swift.user'}
        self.mock_uid.start()

        config = {
            'return_value.id': '12346789',
            'return_value.display_name': 'swift.user',
        }
        self.mock_exists = mock.patch('addons.swift.views.utils.container_exists', **config)
        self.mock_exists.return_value = True
        self.mock_exists.start()

        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.is_staff = True
        self.user.save()

    def tearDown(self):
        self.mock_can_list.stop()
        self.mock_uid.stop()
        self.mock_exists.stop()
        super(TestConnection, self).tearDown()

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.user = self.user
        return views.TestConnectionView.as_view()(request, institution_id=self.institution.id)

    def test_empty_values(self):
        params = {
            'swift_auth_version': '',
            'swift_auth_url': '',
            'swift_access_key': '',
            'swift_secret_key': '',
            'swift_tenant_name': '',
            'swift_container': '',
            'provider_short_name': 'swift',
        }
        request_post_response = self.view_post(params)
        assert (request_post_response.status_code) == (http_status.HTTP_400_BAD_REQUEST)
        assert ('All the fields above are required.') in (request_post_response.content.decode())

    def test_empty_user_domain_name(self):
        params = {
            'swift_auth_version': '3',
            'swift_auth_url': 'Non-empty-auth-url',
            'swift_access_key': 'Non-empty-access-key',
            'swift_secret_key': 'Non-empty-secret-key',
            'swift_tenant_name': 'Non-empty-tenant_name',
            'swift_user_domain_name': '',
            'swift_project_domain_name': 'Non-empty-project_domain_name',
            'swift_container': 'Non-empty-container',
            'provider_short_name': 'swift',
        }
        request_post_response = self.view_post(params)
        assert (request_post_response.status_code) == (http_status.HTTP_400_BAD_REQUEST)
        assert ('The field `user_domain_name` is required when you choose identity V3.') in (request_post_response.content.decode())

    def test_empty_project_domain_name(self):
        params = {
            'swift_auth_version': '3',
            'swift_auth_url': 'Non-empty-auth-url',
            'swift_access_key': 'Non-empty-access-key',
            'swift_secret_key': 'Non-empty-secret-key',
            'swift_tenant_name': 'Non-empty-tenant_name',
            'swift_user_domain_name': 'Non-empty-user_domain_name',
            'swift_project_domain_name': '',
            'swift_container': 'Non-empty-container',
            'provider_short_name': 'swift',
        }
        request_post_response = self.view_post(params)
        assert (request_post_response.status_code) == (http_status.HTTP_400_BAD_REQUEST)
        assert ('The field `project_domain_name` is required when you choose identity V3.') in (request_post_response.content.decode())

    @mock.patch('addons.swift.views.utils.get_user_info', return_value=None)
    def test_invalid_credentials(self, mock_uid):
        params = {
            'swift_auth_version': '3',
            'swift_auth_url': 'Non-empty-auth-url',
            'swift_access_key': 'Non-empty-access-key',
            'swift_secret_key': 'Non-empty-secret-key',
            'swift_tenant_name': 'Non-empty-tenant_name',
            'swift_user_domain_name': 'Non-empty-user_domain_name',
            'swift_project_domain_name': 'Non-empty-project_domain_name',
            'swift_container': 'Non-empty-container',
            'provider_short_name': 'swift',
        }
        request_post_response = self.view_post(params)
        assert (request_post_response.status_code) == (http_status.HTTP_400_BAD_REQUEST)
        assert ('Unable to access account.\\n'
                'Check to make sure that the above credentials are valid, '
                'and that they have permission to list containers.') in (request_post_response.content.decode())

    @mock.patch('addons.swift.views.utils.connect_swift')
    def test_cant_list(self, mock_connect):
        mock_connect.side_effect = swift_exceptions.ClientException('NG')

        params = {
            'swift_auth_version': '3',
            'swift_auth_url': 'Non-empty-auth-url',
            'swift_access_key': 'Non-empty-access-key',
            'swift_secret_key': 'Non-empty-secret-key',
            'swift_tenant_name': 'Non-empty-tenant_name',
            'swift_user_domain_name': 'Non-empty-user_domain_name',
            'swift_project_domain_name': 'Non-empty-project_domain_name',
            'swift_container': 'Non-empty-container',
            'provider_short_name': 'swift',
        }
        request_post_response = self.view_post(params)
        assert (request_post_response.status_code) == (http_status.HTTP_400_BAD_REQUEST)
        assert ('Unable to list containers.\\n'
                'Listing containers is required permission.') in (request_post_response.content.decode())

    @mock.patch('addons.swift.views.utils.connect_swift')
    def test_invalid_container(self, mock_connect):
        containers = [
            {'name': 'Dog'},
            {'name': 'Pigeon'},
        ]
        mock_connect.return_value.get_account.return_value = None, containers

        params = {
            'swift_auth_version': '3',
            'swift_auth_url': 'Non-empty-auth-url',
            'swift_access_key': 'Non-empty-access-key',
            'swift_secret_key': 'Non-empty-secret-key',
            'swift_tenant_name': 'Non-empty-tenant_name',
            'swift_user_domain_name': 'Non-empty-user_domain_name',
            'swift_project_domain_name': 'Non-empty-project_domain_name',
            'swift_container': 'Kitty',
            'provider_short_name': 'swift',
        }
        request_post_response = self.view_post(params)
        assert (request_post_response.status_code) == (http_status.HTTP_400_BAD_REQUEST)
        assert ('Invalid container name.') in (request_post_response.content.decode())

    @mock.patch('addons.swift.views.utils.connect_swift')
    def test_valid_container(self, mock_connect):
        containers = [
            {'name': 'Dog'},
            {'name': 'Kitty'},
            {'name': 'Pigeon'},
        ]
        mock_connect.return_value.get_account.return_value = None, containers

        params = {
            'swift_auth_version': '3',
            'swift_auth_url': 'Non-empty-auth-url',
            'swift_access_key': 'Non-empty-access-key',
            'swift_secret_key': 'Non-empty-secret-key',
            'swift_tenant_name': 'Non-empty-tenant_name',
            'swift_user_domain_name': 'Non-empty-user_domain_name',
            'swift_project_domain_name': 'Non-empty-project_domain_name',
            'swift_container': 'Kitty',
            'provider_short_name': 'swift',
        }
        request_post_response = self.view_post(params)
        assert (request_post_response.status_code) == (http_status.HTTP_200_OK)
        assert ('Credentials are valid') in (request_post_response.content.decode())


class TestSaveCredentials(AdminTestCase):

    def setUp(self):
        super(TestSaveCredentials, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.is_staff = True
        self.user.save()

    def view_post(self, params):
        request = RequestFactory().post(
            'fake_path',
            json.dumps(params),
            content_type='application/json'
        )
        request.user = self.user
        return views.SaveCredentialsView.as_view()(request, institution_id=self.institution.id)

    def test_provider_missing(self):
        response = self.view_post({
            'storage_name': 'Rando Randerson\'s storage',
            'auth_version': '3 I guess?',
            'access_key': 'Non-empty-access-key',
            'secret_key': 'Non-empty-secret-key',
            'tenant_name': 'Non-empty-tenant-name',
            'user_domain_name': 'Non-empty-user-domain-name',
            'project_domain_name': 'Non-empty-project-domain-name',
            'auth_url': 'Non-empty-auth-url',
            'folder': 'Non-empty-folder',
            'container': 'Non-empty-container',
        })

        assert (response.status_code) == (http_status.HTTP_400_BAD_REQUEST)
        assert ('Provider is missing.') in (response.content.decode())

    def test_invalid_provider(self):
        response = self.view_post({
            'storage_name': 'Rando Randerson\'s storage',
            'auth_version': '3 I guess?',
            'access_key': 'Non-empty-access-key',
            'secret_key': 'Non-empty-secret-key',
            'tenant_name': 'Non-empty-tenant-name',
            'user_domain_name': 'Non-empty-user-domain-name',
            'project_domain_name': 'Non-empty-project-domain-name',
            'auth_url': 'Non-empty-auth-url',
            'folder': 'Non-empty-folder',
            'container': 'Non-empty-container',
            'provider_short_name': 'invalidprovider',
        })

        assert (response.status_code) == (http_status.HTTP_400_BAD_REQUEST)
        assert ('Invalid provider.') in (response.content.decode())

    @mock.patch('admin.rdm_custom_storage_location.utils.test_swift_connection')
    def test_success(self, mock_testconnection):
        mock_testconnection.return_value = {'message': 'Nice'}, http_status.HTTP_200_OK
        response = self.view_post({
            'storage_name': 'My storage',
            'swift_auth_version': '3 I guess?',
            'swift_access_key': 'Non-empty-access-key',
            'swift_secret_key': 'Non-empty-secret-key',
            'swift_tenant_name': 'Non-empty-tenant-name',
            'swift_user_domain_name': 'Non-empty-user-domain-name',
            'swift_project_domain_name': 'Non-empty-project-domain-name',
            'swift_auth_url': 'Non-empty-auth-url',
            'swift_container': 'Non-empty-container',
            'provider_short_name': 'swift',
        })

        assert (response.status_code) == (http_status.HTTP_200_OK)
        assert ('Saved credentials successfully!!') in (response.content.decode())

        institution_storage = Region.objects.filter(_id=self.institution._id).first()
        assert (institution_storage) is not None
        assert (institution_storage.name) == ('My storage')

        wb_credentials = institution_storage.waterbutler_credentials
        assert (wb_credentials['storage']['username']) == ('Non-empty-access-key')
        assert (wb_credentials['storage']['password']) == ('Non-empty-secret-key')

        wb_settings = institution_storage.waterbutler_settings
        assert (wb_settings['storage']['provider']) == ('swift')
        assert (wb_settings['storage']['container']) == ('Non-empty-container')

    @mock.patch('admin.rdm_custom_storage_location.utils.test_swift_connection')
    def test_invalid_credentials(self, mock_testconnection):
        mock_testconnection.return_value = {'message': 'NG'}, http_status.HTTP_400_BAD_REQUEST

        response = self.view_post({
            'storage_name': 'My storage',
            'swift_auth_version': '3 I guess?',
            'swift_access_key': 'Wrong access key',
            'swift_secret_key': 'Wrong secret key',
            'swift_tenant_name': 'Non-empty-tenant-name',
            'swift_user_domain_name': 'Non-empty-user-domain-name',
            'swift_project_domain_name': 'Non-empty-project-domain-name',
            'swift_auth_url': 'Non-empty-auth-url',
            'swift_container': 'Non-empty-container',
            'provider_short_name': 'swift',
        })

        assert (response.status_code) == (http_status.HTTP_400_BAD_REQUEST)
        assert ('NG') in (response.content.decode())
        assert not (Region.objects.filter(_id=self.institution._id).exists())

    @mock.patch('admin.rdm_custom_storage_location.utils.test_swift_connection')
    def test_success_superuser(self, mock_testconnection):
        self.user.affiliated_institutions.clear()
        self.user.is_superuser = True
        self.user.save()
        mock_testconnection.return_value = {'message': 'Nice'}, http_status.HTTP_200_OK
        response = self.view_post({
            'storage_name': 'My storage',
            'swift_auth_version': '3 I guess?',
            'swift_access_key': 'Non-empty-access-key',
            'swift_secret_key': 'Non-empty-secret-key',
            'swift_tenant_name': 'Non-empty-tenant-name',
            'swift_user_domain_name': 'Non-empty-user-domain-name',
            'swift_project_domain_name': 'Non-empty-project-domain-name',
            'swift_auth_url': 'Non-empty-auth-url',
            'swift_container': 'Non-empty-container',
            'provider_short_name': 'swift',
        })

        assert (response.status_code) == (http_status.HTTP_200_OK)
        assert ('Saved credentials successfully!!') in (response.content.decode())

        institution_storage = Region.objects.filter(_id=self.institution._id).first()
        assert (institution_storage) is not None
        assert (institution_storage.name) == ('My storage')

        wb_credentials = institution_storage.waterbutler_credentials
        assert (wb_credentials['storage']['username']) == ('Non-empty-access-key')
        assert (wb_credentials['storage']['password']) == ('Non-empty-secret-key')

        wb_settings = institution_storage.waterbutler_settings
        assert (wb_settings['storage']['provider']) == ('swift')
        assert (wb_settings['storage']['container']) == ('Non-empty-container')
