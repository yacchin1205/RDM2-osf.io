from website.addons.base.serializer import OAuthAddonSerializer
from website.addons.weko import client
from website.addons.weko import settings as weko_settings
from website.util import api_url_for, web_url_for


class WEKOSerializer(OAuthAddonSerializer):

    addon_short_name = 'weko'

    REQUIRED_URLS = []

    # Include host information with more informative labels / formatting
    def serialize_account(self, external_account):
        ret = super(WEKOSerializer, self).serialize_account(external_account)
        host = external_account.oauth_key
        ret.update({
            'host': host,
            'host_url': 'https://{0}'.format(host),
        })

        return ret

    @property
    def credentials_owner(self):
        return self.node_settings.user_settings.owner

    @property
    def serialized_urls(self):
        external_account = self.node_settings.external_account
        ret = {
            'settings': web_url_for('user_addons'),  # TODO: Is this needed?
        }
        if external_account and external_account.profile_url:
            ret['owner'] = external_account.profile_url

        addon_urls = self.addon_serialized_urls
        # Make sure developer returns set of needed urls
        for url in self.REQUIRED_URLS:
            assert url in addon_urls, "addon_serilized_urls must include key '{0}'".format(url)
        ret.update(addon_urls)
        return ret

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        external_account = self.node_settings.external_account
        host = external_account.oauth_key if external_account else ''

        return {
            'auth': api_url_for('weko_oauth_connect',
                                repoid='<repoid>'),
            'create': api_url_for('weko_add_user_account'),
            'set': node.api_url_for('weko_set_config'),
            'importAuth': node.api_url_for('weko_import_auth'),
            'deauthorize': node.api_url_for('weko_deauthorize_node'),
            'accounts': api_url_for('weko_account_list'),
        }

    @property
    def serialized_node_settings(self):
        result = super(WEKOSerializer, self).serialized_node_settings
        result['repositories'] = weko_settings.REPOSITORY_IDS

        # Update with WEKO specific fields
        if self.node_settings.has_auth:
            connection = client.connect_from_settings(weko_settings, self.node_settings)
            all_indices = client.get_all_indices(connection)
            indices = list(filter(lambda i: i.nested == 0, all_indices))

            result.update({
                'connected': connection is not None,
                'indices': [
                    {'title': index.title, 'id': index.identifier, 'about': index.about}
                    for index in indices
                ],
                'savedIndex': {
                    'title': self.node_settings.index_title,
                    'id': self.node_settings.index_id,
                }
            })

        return result

    def serialize_settings(self, node_settings, user):
        if not self.node_settings:
            self.node_settings = node_settings
        if not self.user_settings:
            self.user_settings = user.get_addon(self.addon_short_name)
        return self.serialized_node_settings
