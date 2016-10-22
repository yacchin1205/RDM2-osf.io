# -*- coding: utf-8 -*-
from website.addons.base.testing import OAuthAddonTestCaseMixin, AddonTestCase
from website.addons.azureblobstorage.provider import AzureBlobStorageProvider
from website.addons.azureblobstorage.serializer import AzureBlobStorageSerializer
from website.addons.azureblobstorage.tests.factories import AzureBlobStorageAccountFactory

class AzureBlobStorageAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'azure1blobstorage'
    ExternalAccountFactory = AzureBlobStorageAccountFactory
    Provider = AzureBlobStorageProvider
    Serializer = AzureBlobStorageSerializer
    client = None
    folder = {
    	'path': 'bucket',
    	'name': 'bucket',
    	'id': 'bucket'
	}
