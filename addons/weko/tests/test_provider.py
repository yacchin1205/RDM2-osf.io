# -*- coding: utf-8 -*-
from unittest import mock

from tests.base import OsfTestCase
from addons.weko.models import WEKOProvider
from addons.weko import settings as weko_settings


class TestProviderScopes(OsfTestCase):

    def setUp(self):
        super(TestProviderScopes, self).setUp()
        self.provider = WEKOProvider()
        self.repo_settings = {
            'host': 'https://test.example.com/sword/',
            'client_id': 'test_client',
            'client_secret': 'test_secret',
            'authorize_url': 'https://test.example.com/oauth/authorize',
            'access_token_url': 'https://test.example.com/oauth/token',
        }
        self.mock_find_repository = mock.patch('addons.weko.provider.find_repository', return_value=self.repo_settings)
        self.mock_find_repository.start()
        self.mock_session = mock.patch('addons.weko.provider.session')
        self.mock_session_obj = self.mock_session.start()
        self.mock_session_obj.data = {'oauth_states': None}
        self.mock_oauth2 = mock.patch('addons.weko.provider.OAuth2Session')
        self.mock_oauth2_class = self.mock_oauth2.start()
        self.mock_oauth2_instance = mock.MagicMock()
        self.mock_oauth2_instance.authorization_url.return_value = ('https://test.example.com/oauth/authorize', 'state')
        self.mock_oauth2_class.return_value = self.mock_oauth2_instance

    def tearDown(self):
        self.mock_find_repository.stop()
        self.mock_session.stop()
        self.mock_oauth2.stop()
        super(TestProviderScopes, self).tearDown()

    def test_default_scopes_with_list(self):
        scopes = ['read', 'write']
        with mock.patch.object(weko_settings, 'DEFAULT_APPLICATION_SCOPES', scopes):
            self.provider.get_repo_auth_url('test.example')
            self.mock_oauth2_class.assert_called_once()
            call_kwargs = self.mock_oauth2_class.call_args[1]
            assert (call_kwargs['scope']) == (scopes)

    def test_default_scopes_with_callable(self):
        def get_scopes(repo_settings):
            if 'test.example.com' in repo_settings['host']:
                return ['read', 'write', 'admin']
            return ['read']

        with mock.patch.object(weko_settings, 'DEFAULT_APPLICATION_SCOPES', get_scopes):
            self.provider.get_repo_auth_url('test.example')
            self.mock_oauth2_class.assert_called_once()
            call_kwargs = self.mock_oauth2_class.call_args[1]
            assert (call_kwargs['scope']) == (['read', 'write', 'admin'])

    def test_callback_includes_client_id_in_token_request(self):
        self.mock_session_obj.data = {
            'oauth_states': {
                self.provider.short_name: {
                    'state': 'test_state',
                    'repoid': 'test.example.com.test_client',
                },
            },
        }
        self.mock_oauth2_instance.fetch_token.return_value = {
            'access_token': 'test_access_token',
        }

        with mock.patch.object(self.provider, '_default_handle_callback', return_value={}), \
                mock.patch.object(self.provider, 'handle_callback', return_value={}), \
                mock.patch.object(self.provider, '_set_external_account', return_value=True):
            with self.app.application.test_request_context(
                    '/oauth/callback/weko/test.example.com/',
                    query_string='code=test_code&state=test_state'):
                self.provider.repo_auth_callback(
                    user=mock.sentinel.user,
                    repodomain='test.example.com',
                )

        self.mock_oauth2_instance.fetch_token.assert_called_once_with(
            self.repo_settings['access_token_url'],
            include_client_id=True,
            client_secret=self.repo_settings['client_secret'],
            code='test_code',
        )
