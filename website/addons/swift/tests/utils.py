# -*- coding: utf-8 -*-
from website.addons.base.testing import OAuthAddonTestCaseMixin, AddonTestCase
from website.addons.swift.provider import SwiftProvider
from website.addons.swift.serializer import SwiftSerializer
from website.addons.swift.tests.factories import SwiftAccountFactory

class SwiftAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'swift'
    ExternalAccountFactory = SwiftAccountFactory
    Provider = SwiftProvider
    Serializer = SwiftSerializer
    client = None
    folder = {
    	'path': 'bucket',
    	'name': 'bucket',
    	'id': 'bucket'
	}
