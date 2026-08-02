# -*- coding: utf-8 -*-


from tests.base import AdminTestCase
from osf_tests.factories import InstitutionFactory

from admin.rdm_addons import utils

import logging
logging.getLogger('website.project.model').setLevel(logging.DEBUG)

class TestRdmAddonOption(AdminTestCase):
    def setUp(self):
        super(TestRdmAddonOption, self).setUp()
        self.institution = InstitutionFactory()

    def tearDown(self):
        super(TestRdmAddonOption, self).tearDown()
        self.institution.delete()

    def test_get_rdm_addon_option_without_create_option(self):
        assert (None) == (utils.get_rdm_addon_option(self.institution.id, 's3', create=False))
        assert (None) == (utils.get_rdm_addon_option(self.institution.id, 'dropboxbusiness', create=False))

    def test_get_is_allowed_default(self):
        # newly created option
        option = utils.get_rdm_addon_option(self.institution.id, 's3')
        assert (option.is_allowed)

        option = utils.get_rdm_addon_option(self.institution.id, 'dropboxbusiness')
        assert not (option.is_allowed)

        # option retrieved from database
        option = utils.get_rdm_addon_option(self.institution.id, 's3', create=False)
        assert (option.is_allowed)

        option = utils.get_rdm_addon_option(self.institution.id, 'dropboxbusiness', create=False)
        assert not (option.is_allowed)
