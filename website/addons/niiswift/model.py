# -*- coding: utf-8 -*-

from modularodm import fields

from framework.auth.core import Auth

from website.addons.base import exceptions
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.addons.base import StorageAddonBase

from website.addons.niiswift.provider import SwiftProvider
from website.addons.niiswift.serializer import SwiftSerializer
from website.addons.niiswift.settings import ENCRYPT_UPLOADS_DEFAULT, BUCKET_LOCATIONS
from website.addons.niiswift.utils import bucket_exists, get_bucket_names, get_bucket_location_or_error


class SwiftUserSettings(AddonOAuthUserSettingsBase):

    oauth_provider = SwiftProvider
    serializer = SwiftSerializer


class SwiftNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):

    oauth_provider = SwiftProvider
    serializer = SwiftSerializer

    folder_id = fields.StringField()
    folder_name = fields.StringField()
    encrypt_uploads = fields.BooleanField(default=ENCRYPT_UPLOADS_DEFAULT)

    @property
    def folder_path(self):
        return self.folder_name

    def fetch_folder_name(self):
        return self.folder_name

    @property
    def display_name(self):
        return u'{0}: {1}'.format(self.config.full_name, self.folder_id)

    def set_folder(self, folder_id, auth):
        if not bucket_exists(self.external_account.oauth_key, self.external_account.oauth_secret, folder_id):
            error_message = ('We are having trouble connecting to that bucket. '
                             'Try a different one.')
            raise exceptions.InvalidFolderError(error_message)

        self.folder_id = str(folder_id)

        bucket_location = get_bucket_location_or_error(
            self.external_account.oauth_key,
            self.external_account.oauth_secret,
            folder_id
        )
        try:
            bucket_location = BUCKET_LOCATIONS[bucket_location]
        except KeyError:
            # Unlisted location, Swift may have added it recently.
            # Default to the key. When hit, add mapping to settings
            pass

        self.folder_name = '{} ({})'.format(folder_id, bucket_location)
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
                'addon': 'niiswift',
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
        return {
            'access_key': self.external_account.oauth_key,
            'secret_key': self.external_account.oauth_secret,
        }

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('Cannot serialize settings for Swift addon')
        return {
            'bucket': self.folder_id,
            'encrypt_uploads': self.encrypt_uploads
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='niiswift')

        self.owner.add_log(
            'niiswift_{0}'.format(action),
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
