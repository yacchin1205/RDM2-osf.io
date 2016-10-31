# -*- coding: utf-8 -*-
import httplib as http

from modularodm import fields

from framework.auth.decorators import Auth
from framework.exceptions import HTTPError
from framework.sessions import session
from requests_oauthlib import OAuth2Session
from flask import request

from website.addons.base import (
    AddonOAuthNodeSettingsBase, AddonOAuthUserSettingsBase, exceptions,
)
from website.addons.base import StorageAddonBase
from website.oauth.models import ExternalProvider
from oauthlib.oauth2.rfc6749.errors import MissingTokenError
from requests.exceptions import HTTPError as RequestsHTTPError

from website.addons.weko.client import connect_or_error, connect_from_settings_or_401
from website.addons.weko.serializer import WEKOSerializer
from website.addons.weko.utils import DataverseNodeLogger
from website.addons.weko import settings as weko_settings
from website.util import web_url_for, api_v2_url

OAUTH2 = 2

class WEKOProvider(ExternalProvider):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'WEKO'
    short_name = 'weko'
    serializer = WEKOSerializer

    client_id = None
    client_secret = None
    auth_url_base = None
    callback_url = None

    def get_repo_auth_url(self, repoid):
        """The URL to begin the OAuth dance.

        This property method has side effects - it at least adds temporary
        information to the session so that callbacks can be associated with
        the correct user.  For OAuth1, it calls the provider to obtain
        temporary credentials to start the flow.
        """

        # create a dict on the session object if it's not already there
        if session.data.get('oauth_states') is None:
            session.data['oauth_states'] = {}

        repo_settings = weko_settings.REPOSITORIES[repoid]

        assert self._oauth_version == OAUTH2
        # build the URL
        oauth = OAuth2Session(
            repo_settings['client_id'],
            redirect_uri=web_url_for('weko_oauth_callback',
                                     repoid=repoid,
                                     _absolute=True),
            scope=self.default_scopes,
        )

        url, state = oauth.authorization_url(repo_settings['authorize_url'])

        # save state token to the session for confirmation in the callback
        session.data['oauth_states'][self.short_name] = {'state': state}

        return url

    def repo_auth_callback(self, user, repoid, **kwargs):
        """Exchange temporary credentials for permanent credentials

        This is called in the view that handles the user once they are returned
        to the OSF after authenticating on the external service.
        """

        if 'error' in request.args:
            return False

        repo_settings = weko_settings.REPOSITORIES[repoid]

        # make sure the user has temporary credentials for this provider
        try:
            cached_credentials = session.data['oauth_states'][self.short_name]
        except KeyError:
            raise PermissionsError('OAuth flow not recognized.')

        assert self._oauth_version == OAUTH2
        state = request.args.get('state')

        # make sure this is the same user that started the flow
        if cached_credentials.get('state') != state:
            raise PermissionsError('Request token does not match')

        try:
            callback_url = web_url_for('weko_oauth_callback', repoid=repoid,
                                       _absolute=True)
            response = OAuth2Session(
                repo_settings['client_id'],
                redirect_uri=callback_url,
            ).fetch_token(
                repo_settings['access_token_url'],
                client_secret=repo_settings['client_secret'],
                code=request.args.get('code'),
            )
        except (MissingTokenError, RequestsHTTPError):
            raise HTTPError(http.SERVICE_UNAVAILABLE)
        # pre-set as many values as possible for the ``ExternalAccount``
        info = self._default_handle_callback(response)
        # call the hook for subclasses to parse values from the response
        info.update(self.handle_callback(repoid, response))

        return self._set_external_account(user, info)

    def handle_callback(self, repoid, response):
        """View called when the OAuth flow is completed.
        """
        repo_settings = weko_settings.REPOSITORIES[repoid]
        connection = connect_or_error(repo_settings['host'],
                                      response.get('access_token'))
        login_user = connection.get_login_user('unknown')
        return {
            'provider_id': login_user + '@' + repoid,
            'display_name': login_user + '@' + repoid
        }


class AddonWEKOUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = WEKOProvider
    serializer = WEKOSerializer

class AddonWEKONodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):
    oauth_provider = WEKOProvider
    serializer = WEKOSerializer

    index_title = fields.StringField()
    index_id = fields.StringField()

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = WEKOProvider(self.external_account)
        return self._api

    @property
    def folder_name(self):
        return self.index_title

    @property
    def complete(self):
        return bool(self.has_auth and self.index_id is not None)

    @property
    def folder_id(self):
        return self.index_id

    @property
    def folder_path(self):
        pass

    @property
    def nodelogger(self):
        # TODO: Use this for all log actions
        auth = None
        if self.user_settings:
            auth = Auth(self.user_settings.owner)
        return DataverseNodeLogger(
            node=self.owner,
            auth=auth
        )

    def set_folder(self, index, auth=None):
        self.index_id = index.identifier
        self.index_title = index.title

        self.save()

        if auth:
            self.owner.add_log(
                action='weko_dataset_linked',
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                    'dataset': index.title,
                },
                auth=auth,
            )

    def _get_fileobj_child_metadata(self, filenode, user, cookie=None, version=None):
        try:
            return super(AddonDataverseNodeSettings, self)._get_fileobj_child_metadata(filenode, user, cookie=cookie, version=version)
        except HTTPError as e:
            # The Dataverse API returns a 404 if the dataset has no published files
            if e.code == http.NOT_FOUND and version == 'latest-published':
                return []
            raise

    def clear_settings(self):
        """Clear selected Dataverse and dataset"""
        self.index_id = None
        self.index_title = None

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()
        self.clear_auth()  # Also performs a save

        # Log can't be added without auth
        if add_log and auth:
            node = self.owner
            self.owner.add_log(
                action='weko_node_deauthorized',
                params={
                    'project': node.parent_id,
                    'node': node._id,
                },
                auth=auth,
            )

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.external_account.oauth_key}

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('Dataverse is not configured')
        return {
            'host': self.external_account.oauth_key,
            'url': weko_settings.REPOSITORIES[self.external_account.provider_id.split('@')[-1]]['host'],
            'index_id': self.index_id,
            'index_title': self.index_title,
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='weko')
        self.owner.add_log(
            'weko_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'dataset': self.dataset,
                'filename': metadata['materialized'].strip('/'),
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )

    ##### Callback overrides #####

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()
