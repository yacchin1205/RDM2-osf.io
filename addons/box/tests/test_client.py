# -*- coding: utf-8 -*-
import pytest
import unittest

from osf_tests.factories import UserFactory

from addons.box.models import UserSettings

pytestmark = pytest.mark.django_db

class TestCore(unittest.TestCase):

    def setUp(self):

        super(TestCore, self).setUp()

        self.user = UserFactory()
        self.user.add_addon('box')
        self.user.save()

        self.settings = self.user.get_addon('box')
        self.settings.save()

    def test_get_addon_returns_box_user_settings(self):
        result = self.user.get_addon('box')
        assert (isinstance(result, UserSettings))
