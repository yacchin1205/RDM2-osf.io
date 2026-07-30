from datetime import datetime

from django.utils import timezone

from tests.base import AdminTestCase
from osf_tests.factories import NodeFactory, UserFactory, PreprintFactory

from admin.users.serializers import serialize_user, serialize_simple_node, serialize_simple_preprint


class TestUserSerializers(AdminTestCase):
    def test_serialize_user(self):
        user = UserFactory()
        info = serialize_user(user)
        assert isinstance((info), (dict))
        assert (info['name']) == (user.fullname)
        assert (info['id']) == (user._id)
        assert (list(info['emails'])) == (list(user.emails.values_list('address', flat=True)))
        assert (info['last_login']) == (user.date_last_login)

    def test_serialize_two_factor(self):
        user = UserFactory()
        info = serialize_user(user)
        assert not (info['two_factor'])
        user.get_or_add_addon('twofactor')
        info = serialize_user(user)
        assert isinstance((info), (dict))
        assert (info['name']) == (user.fullname)
        assert (list(info['emails'])) == (list(user.emails.values_list('address', flat=True)))
        assert (info['last_login']) == (user.date_last_login)
        assert (info['two_factor'])

    def test_serialize_account_status(self):
        user = UserFactory()
        info = serialize_user(user)
        assert (info['disabled']) == (False)
        user.is_disabled = True
        info = serialize_user(user)
        assert abs((int(info['disabled'].strftime('%s'))) - (int(timezone.now().strftime('%s')))) <= (50)
        assert isinstance((info['disabled']), (datetime))

    def test_serialize_simple_node(self):
        node = NodeFactory()
        info = serialize_simple_node(node)
        assert isinstance((info), (dict))
        assert (info['id']) == (node._id)
        assert (info['title']) == (node.title)
        assert (info['public']) == (node.is_public)
        assert (info['number_contributors']) == (len(node.contributors))

    def test_serialize_simple_preprint(self):
        preprint = PreprintFactory()
        info = serialize_simple_preprint(preprint)
        assert isinstance((info), (dict))
        assert (info['id']) == (preprint._id)
        assert (info['title']) == (preprint.title)
        assert (info['public']) == (preprint.verified_publishable)
        assert (info['number_contributors']) == (len(preprint.contributors))
