
from tests.base import AdminTestCase

from admin.base.forms import GuidForm


class TestGuidForm(AdminTestCase):
    def setUp(self):
        super(TestGuidForm, self).setUp()

    def test_valid_data(self):
        guid = '12345'
        form = GuidForm({
            'guid': guid,
        })
        assert (form.is_valid())
        assert (form.cleaned_data.get('guid')) == (guid)

    def test_blank_data(self):
        form = GuidForm({})
        assert not (form.is_valid())
        assert (form.errors) == ({
            'guid': [u'This field is required.'],
        })
