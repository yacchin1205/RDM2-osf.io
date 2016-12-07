# -*- coding: utf-8 -*-
"""Factories for the S3 addon."""
from factory import SubFactory, Sequence
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

from website.addons.azureblobstorage.model import (
    AzureBlobStorageUserSettings,
    AzureBlobStorageNodeSettings
)

class AzureBlobStorageAccountFactory(ExternalAccountFactory):
    provider = 'azureblobstorage'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = Sequence(lambda n:'secret-{0}'.format(n))
    display_name = 'Azure Blob Storage Fake User'


class AzureBlobStorageUserSettingsFactory(ModularOdmFactory):
    class Meta:
        model = AzureBlobStorageUserSettings

    owner = SubFactory(UserFactory)


class AzureBlobStorageNodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model =  AzureBlobStorageNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(AzureBlobStorageUserSettingsFactory)
    bucket = 'mock_bucket'
