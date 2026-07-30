
from tests.base import AdminTestCase
from osf_tests.factories import NodeFactory, UserFactory
from osf.utils.permissions import ADMIN
from admin.nodes.serializers import serialize_simple_user_and_node_permissions, serialize_node


class TestNodeSerializers(AdminTestCase):
    def test_serialize_node(self):
        node = NodeFactory()
        info = serialize_node(node)
        assert isinstance((info), (dict))
        assert (info['parent']) == (node.parent_id)
        assert (info['title']) == (node.title)
        assert (info['children']) == ([])
        assert (info['id']) == (node._id)
        assert (info['public']) == (node.is_public)
        assert (len(info['contributors'])) == (1)
        assert not (info['deleted'])

    def test_serialize_deleted(self):
        node = NodeFactory()
        info = serialize_node(node)
        assert not (info['deleted'])
        node.is_deleted = True
        info = serialize_node(node)
        assert (info['deleted'])
        node.is_deleted = False
        info = serialize_node(node)
        assert not (info['deleted'])

    def test_serialize_simple_user(self):
        user = UserFactory()
        node = NodeFactory(creator=user)
        info = serialize_simple_user_and_node_permissions(node, user)
        assert isinstance((info), (dict))
        assert (info['id']) == (user._id)
        assert (info['name']) == (user.fullname)
        assert (info['permission']) == (ADMIN)
