# -*- coding: utf-8 -*-
from website.addons.base.testing import OAuthAddonTestCaseMixin, AddonTestCase
from website.addons.niiswift.provider import SwiftProvider
from website.addons.niiswift.serializer import SwiftSerializer
from website.addons.niiswift.tests.factories import SwiftAccountFactory

class SwiftAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'niiswift'
    ExternalAccountFactory = SwiftAccountFactory
    Provider = SwiftProvider
    Serializer = SwiftSerializer
    client = None
    folder = {
    	'path': 'bucket',
    	'name': 'bucket',
    	'id': 'bucket'
	}
