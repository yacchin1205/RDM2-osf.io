# -*- coding: utf-8 -*-
from framework.exceptions import HTTPError

from addons.onedrive import settings # using base settings
from addons.onedrive.client import OneDriveClient


class OneDriveBusinessClient(OneDriveClient):

    def __init__(self, access_token=None):
        super(OneDriveBusinessClient, self).__init__(access_token=access_token)

    def create_folder(self, parent_folder_id, name):
        """Create new folder in ``parent_folder_id`` with ``name``

        API Docs:  https://docs.microsoft.com/en-us/graph/api/driveitem-post-children

        :param str parent_folder_id: the id of the parent folder.
        :param str name: the name of new folder.
        :rtype: dict
        :return: a metadata object representing the new folder
        """

        if parent_folder_id is None or parent_folder_id == settings.DEFAULT_ROOT_ID:
            url = self._build_url(settings.ONEDRIVE_API_URL, 'drive', settings.DEFAULT_ROOT_ID, 'children')
        else:
            url = self._build_url(settings.ONEDRIVE_API_URL, 'drive', 'items',
                                  parent_folder_id, 'children')

        res = self._make_request(
            'POST',
            url,
            json={
                'name': name,
                'folder': {},
                '@microsoft.graph.conflictBehavior': 'fail'
            },
            expects=(200, 201),
            throws=HTTPError(401)
        )
        return res.json()

    def rename_folder(self, folder_id, name):
        """Rename a folder specified by ``folder_id`` with ``name``

        API Docs:  https://docs.microsoft.com/en-us/graph/api/driveitem-update

        :param str folder_id: the id of the folder.
        :param str name: the name of the folder.
        :rtype: dict
        :return: a metadata object representing the folder
        """

        if folder_id is None or folder_id == settings.DEFAULT_ROOT_ID:
            url = self._build_url(settings.ONEDRIVE_API_URL, 'drive', settings.DEFAULT_ROOT_ID)
        else:
            url = self._build_url(settings.ONEDRIVE_API_URL, 'drive', 'items', folder_id)

        res = self._make_request(
            'PATCH',
            url,
            json={
                'name': name,
            },
            expects=(200,),
            throws=HTTPError(401)
        )
        return res.json()
