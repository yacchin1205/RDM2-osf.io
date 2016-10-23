# -*- coding: utf-8 -*-

from modularodm import fields

from framework.auth.core import Auth

from website.addons.base import exceptions
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.addons.base import StorageAddonBase
from website.oauth.models import BasicAuthProviderMixin

from website.addons.swift.serializer import SwiftSerializer
from website.addons.swift.utils import container_exists, get_bucket_names


class SwiftProvider(BasicAuthProviderMixin):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'NII Swift'
    short_name = 'swift'

    def __init__(self, account=None, tenant_name=None, username=None, password=None):
        if username:
            username = username.lower()
        return super(SwiftProvider, self).__init__(account=account, host=tenant_name, username=username, password=password)

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.display_name if self.account else 'anonymous'
        )


class SwiftUserSettings(AddonOAuthUserSettingsBase):

    oauth_provider = SwiftProvider
    serializer = SwiftSerializer


class SwiftNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):

    oauth_provider = SwiftProvider
    serializer = SwiftSerializer

    folder_id = fields.StringField()
    folder_name = fields.StringField()

    _api = None

    @property
    def api(self):
        if self._api is None:
            self._api = SwiftProvider(self.external_account)
        return self._api

    @property
    def folder_path(self):
        return self.folder_name

    def fetch_folder_name(self):
        return self.folder_name

    @property
    def display_name(self):
        return u'{0}: {1}'.format(self.config.full_name, self.folder_id)

    def set_folder(self, folder_id, auth):
        if not container_exists(self.external_account.oauth_key, self.external_account.oauth_secret, folder_id):
            error_message = ('We are having trouble connecting to that bucket. '
                             'Try a different one.')
            raise exceptions.InvalidFolderError(error_message)

        self.folder_id = str(folder_id)
        self.folder_name = str(folder_id)
        self.save()

        self.nodelogger.log(action='bucket_linked', extra={'bucket': str(folder_id)}, save=True)

    def get_folders(self, **kwargs):
        # This really gets only buckets, not subfolders,
        # as that's all we want to be linkable on a node.
        try:
            buckets = get_bucket_names(self)
        except:
            raise exceptions.InvalidAuthError()

        return [
            {
                'addon': 'swift',
                'kind': 'folder',
                'id': bucket,
                'name': bucket,
                'path': bucket,
                'urls': {
                    'folders': ''
                }
            }
            for bucket in buckets
        ]

    @property
    def complete(self):
        return self.has_auth and self.folder_id is not None

    def authorize(self, user_settings, save=False):
        self.user_settings = user_settings
        self.nodelogger.log(action='node_authorized', save=save)

    def clear_settings(self):
        self.folder_id = None
        self.folder_name = None

    def deauthorize(self, auth=None, log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()
        self.clear_auth()  # Also performs a save

        if log:
            self.nodelogger.log(action='node_deauthorized', save=True)

    def delete(self, save=True):
        self.deauthorize(log=False)
        super(SwiftNodeSettings, self).delete(save=save)

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Cannot serialize credentials for Swift addon')
        provider = SwiftProvider(self.external_account)
        return {
            'tenant_name': provider.host,
            'username': provider.username,
            'password': provider.password
        }

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('Cannot serialize settings for Swift addon')
        return {
            'container': self.folder_id
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='swift')

        self.owner.add_log(
            'swift_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': metadata['materialized'],
                'bucket': self.folder_id,
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                }
            },
        )

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), log=True)
