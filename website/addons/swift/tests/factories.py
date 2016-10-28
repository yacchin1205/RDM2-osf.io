# -*- coding: utf-8 -*-
"""Factories for the S3 addon."""
from factory import SubFactory, Sequence
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

from website.addons.swift.model import (
    SwiftUserSettings,
    SwiftNodeSettings
)

class SwiftAccountFactory(ExternalAccountFactory):
    provider = 'swift'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = Sequence(lambda n:'secret-{0}'.format(n))
    display_name = 'NII Swift Fake User'


class SwiftUserSettingsFactory(ModularOdmFactory):
    class Meta:
        model = SwiftUserSettings

    owner = SubFactory(UserFactory)


class SwiftNodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model =  SwiftNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(SwiftUserSettingsFactory)
    bucket = 'mock_bucket'
