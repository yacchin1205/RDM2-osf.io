# -*- coding: utf-8 -*-
from wtforms import Form, Field

from framework.auth import forms

from tests.base import OsfTestCase
from osf_tests.factories import UserFactory, UnregUserFactory


class TestValidation(OsfTestCase):

    def test_no_html_validator_allows_missing_optional_value(self):
        class MockForm(Form):
            name = Field('Name', [forms.NoHtmlCharacters()])

        assert MockForm().validate()

    def test_no_html_validator_rejects_html(self):
        class MockForm(Form):
            name = Field('Name', [forms.NoHtmlCharacters()])

        form = MockForm(name='<strong>Name</strong>')

        assert not form.validate()
        assert 'name' in form.errors

    def test_unique_email_validator(self):
        class MockForm(Form):
            username = Field('Username', [forms.UniqueEmail()])
        u = UserFactory()
        f = MockForm(username=u.username)
        f.validate()
        assert ('username') in (f.errors)

    def test_unique_email_validator_with_unreg_user(self):
        class MockForm(Form):
            username = Field(
                'Username',
                [forms.UniqueEmail(allow_unregistered=True)]
            )
        u = UnregUserFactory()
        f = MockForm(username=u.username)
        assert (f.validate())
