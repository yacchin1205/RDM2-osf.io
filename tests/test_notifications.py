import collections
import datetime
import mock
import pytz
from babel import dates, Locale
from schema import Schema, And, Use, Optional, Or

from mako.lookup import Template
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from nose.tools import *  # noqa PEP8 asserts

from framework.auth import Auth
from framework.auth.core import User
from framework.auth.signals import contributor_removed
from framework.auth.signals import node_deleted
from scripts.send_digest import group_digest_notifications_by_user
from scripts.send_digest import group_messages_by_node
from scripts.send_digest import remove_sent_digest_notifications
from scripts.send_digest import send_digest
from website.notifications import constants
from website.notifications.model import NotificationDigest
from website.notifications.model import NotificationSubscription
from website.notifications import emails
from website.notifications import utils
from website.project.model import Node
from website import mails
from website.util import api_url_for
from website.util import web_url_for

from tests import factories
from tests.base import capture_signals
from tests.base import OsfTestCase


class TestNotificationsModels(OsfTestCase):

    def setUp(self):
        super(TestNotificationsModels, self).setUp()
        # Create project with component
        self.user = factories.UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.parent = factories.ProjectFactory(creator=self.user)
        self.node = factories.NodeFactory(creator=self.user, parent=self.parent)

    def test_can_read_children(self):
        non_admin_user = factories.UserFactory()
        parent = factories.ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=['read'])
        parent.save()

        node = factories.NodeFactory(parent=parent, category='project')
        sub_component = factories.NodeFactory(parent=node)
        sub_component.add_contributor(contributor=non_admin_user)
        sub_component.save()
        sub_component2 = factories.NodeFactory(parent=node)

        has_permission_on_child_node = node.can_read_children(non_admin_user)
        assert_true(has_permission_on_child_node)

    def test_check_user_has_permission_excludes_deleted_components(self):
        non_admin_user = factories.UserFactory()
        parent = factories.ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=['read'])
        parent.save()

        node = factories.NodeFactory(parent=parent, category='project')
        sub_component = factories.NodeFactory(parent=node)
        sub_component.add_contributor(contributor=non_admin_user)
        sub_component.is_deleted = True
        sub_component.save()
        sub_component2 = factories.NodeFactory(parent=node)

        has_permission_on_child_node = node.can_read_children(non_admin_user)
        assert_false(has_permission_on_child_node)

    def test_check_user_does_not_have_permission_on_private_node_child(self):
        non_admin_user = factories.UserFactory()
        parent = factories.ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=['read'])
        parent.save()
        node = factories.NodeFactory(parent=parent, category='project')
        sub_component = factories.NodeFactory(parent=node)
        has_permission_on_child_node = node.can_read_children(non_admin_user)
        assert_false(has_permission_on_child_node)

    def test_check_user_child_node_permissions_false_if_no_children(self):
        non_admin_user = factories.UserFactory()
        parent = factories.ProjectFactory()
        parent.add_contributor(contributor=non_admin_user, permissions=['read'])
        parent.save()
        node = factories.NodeFactory(parent=parent, category='project')
        has_permission_on_child_node = node.can_read_children(non_admin_user)
        assert_false(has_permission_on_child_node)

    def test_check_admin_has_permissions_on_private_component(self):
        parent = factories.ProjectFactory()
        node = factories.NodeFactory(parent=parent, category='project')
        sub_component = factories.NodeFactory(parent=node)
        has_permission_on_child_node = node.can_read_children(parent.creator)
        assert_true(has_permission_on_child_node)

    def test_check_user_private_node_child_permissions_excludes_pointers(self):
        user = factories.UserFactory()
        parent = factories.ProjectFactory()
        pointed = factories.ProjectFactory(contributor=user)
        parent.add_pointer(pointed, Auth(parent.creator))
        parent.save()
        has_permission_on_child_nodes = parent.can_read_children(user)
        assert_false(has_permission_on_child_nodes)


class TestSubscriptionView(OsfTestCase):

    def setUp(self):
        super(TestSubscriptionView, self).setUp()
        self.node = factories.NodeFactory()
        self.user = self.node.creator

    def test_create_new_subscription(self):
        payload = {
            'id': self.node._id,
            'event': 'comments',
            'notification_type': 'email_transactional'
        }
        url = api_url_for('configure_subscription')
        self.app.post_json(url, payload, auth=self.node.creator.auth)

        # check that subscription was created
        event_id = self.node._id + '_' + 'comments'
        s = NotificationSubscription.find_one(Q('_id', 'eq', event_id))

        # check that user was added to notification_type field
        assert_equal(payload['id'], s.owner._id)
        assert_equal(payload['event'], s.event_name)
        assert_in(self.node.creator, getattr(s, payload['notification_type']))

        # change subscription
        new_payload = {
            'id': self.node._id,
            'event': 'comments',
            'notification_type': 'email_digest'
        }
        url = api_url_for('configure_subscription')
        self.app.post_json(url, new_payload, auth=self.node.creator.auth)
        s.reload()
        assert_false(self.node.creator in getattr(s, payload['notification_type']))
        assert_in(self.node.creator, getattr(s, new_payload['notification_type']))

    def test_adopt_parent_subscription_default(self):
        payload = {
            'id': self.node._id,
            'event': 'comments',
            'notification_type': 'adopt_parent'
        }
        url = api_url_for('configure_subscription')
        self.app.post_json(url, payload, auth=self.node.creator.auth)
        event_id = self.node._id + '_' + 'comments'
        # confirm subscription was not created
        with assert_raises(NoResultsFound):
            NotificationSubscription.find_one(Q('_id', 'eq', event_id))

    def test_change_subscription_to_adopt_parent_subscription_removes_user(self):
        payload = {
            'id': self.node._id,
            'event': 'comments',
            'notification_type': 'email_transactional'
        }
        url = api_url_for('configure_subscription')
        self.app.post_json(url, payload, auth=self.node.creator.auth)

        # check that subscription was created
        event_id = self.node._id + '_' + 'comments'
        s = NotificationSubscription.find_one(Q('_id', 'eq', event_id))

        # change subscription to adopt_parent
        new_payload = {
            'id': self.node._id,
            'event': 'comments',
            'notification_type': 'adopt_parent'
        }
        url = api_url_for('configure_subscription')
        self.app.post_json(url, new_payload, auth=self.node.creator.auth)
        s.reload()

        # assert that user is removed from the subscription entirely
        for n in constants.NOTIFICATION_TYPES:
            assert_false(self.node.creator in getattr(s, n))


class TestRemoveContributor(OsfTestCase):
    def setUp(self):
        super(OsfTestCase, self).setUp()
        self.project = factories.ProjectFactory()
        self.contributor = factories.UserFactory()
        self.project.add_contributor(contributor=self.contributor, permissions=['read'])
        self.project.save()

        self.subscription = factories.NotificationSubscriptionFactory(
            _id=self.project._id + '_comments',
            owner=self.project
        )
        self.subscription.save()
        self.subscription.email_transactional.append(self.contributor)
        self.subscription.email_transactional.append(self.project.creator)
        self.subscription.save()

        self.node = factories.NodeFactory(parent=self.project)
        self.node.add_contributor(contributor=self.project.creator, permissions=['read', 'write', 'admin'])
        self.node.save()
        self.node_subscription = factories.NotificationSubscriptionFactory(
            _id=self.node._id + '_comments',
            owner=self.node
        )
        self.node_subscription.save()
        self.node_subscription.email_transactional.append(self.project.creator)
        self.node_subscription.email_transactional.append(self.node.creator)
        self.node_subscription.save()

    def test_removed_non_admin_contributor_is_removed_from_subscriptions(self):
        assert_in(self.contributor, self.subscription.email_transactional)
        self.project.remove_contributor(self.contributor, auth=Auth(self.project.creator))
        assert_not_in(self.contributor, self.project.contributors)
        assert_not_in(self.contributor, self.subscription.email_transactional)

    def test_removed_non_parent_admin_contributor_is_removed_from_subscriptions(self):
        assert_in(self.node.creator, self.node_subscription.email_transactional)
        self.node.remove_contributor(self.node.creator, auth=Auth(self.node.creator))
        assert_not_in(self.node.creator, self.node.contributors)
        assert_not_in(self.node.creator, self.node_subscription.email_transactional)

    def test_removed_contributor_admin_on_parent_not_removed_from_node_subscription(self):
        # Admin on parent project is removed as a contributor on a component. Check
        #     that admin is not removed from component subscriptions, as the admin
        #     now has read-only access.
        assert_in(self.project.creator, self.node_subscription.email_transactional)
        self.node.remove_contributor(self.project.creator, auth=Auth(self.project.creator))
        assert_not_in(self.project.creator, self.node.contributors)
        assert_in(self.project.creator, self.node_subscription.email_transactional)

    def test_remove_contributor_signal_called_when_contributor_is_removed(self):
        with capture_signals() as mock_signals:
            self.project.remove_contributor(self.contributor, auth=Auth(self.project.creator))
        assert_equal(mock_signals.signals_sent(), set([contributor_removed]))


class TestRemoveNodeSignal(OsfTestCase):
        def test_node_subscriptions_and_backrefs_removed_when_node_is_deleted(self):
            project = factories.ProjectFactory()
            subscription = factories.NotificationSubscriptionFactory(
                _id=project._id + '_comments',
                owner=project
            )
            subscription.save()
            subscription.email_transactional.append(project.creator)
            subscription.save()

            s = getattr(project.creator, 'email_transactional', [])
            assert_equal(len(s), 1)

            with capture_signals() as mock_signals:
                project.remove_node(auth=Auth(project.creator))
            assert_true(project.is_deleted)
            assert_equal(mock_signals.signals_sent(), set([node_deleted]))

            s = getattr(project.creator, 'email_transactional', [])
            assert_equal(len(s), 0)

            with assert_raises(NoResultsFound):
                NotificationSubscription.find_one(Q('owner', 'eq', project))


def list_or_dict(data):
    """Generator only returns lists or dicts from list or dict"""
    if isinstance(data, dict):
        for key in data:
            if isinstance(data[key], dict) or isinstance(data[key], list):
                yield data[key]
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) or isinstance(item, list):
                yield item


def has(data, sub_data):
    """
    Recursive approach to look for a subset of data in data.
    WARNING: Don't use on huge structures
    :param data: Data structure
    :param sub_data: subset being checked for
    :return: True or False
    """
    try:
        (item for item in data if item == sub_data).next()
        return True
    except StopIteration:
        lists_and_dicts = list_or_dict(data)
        for item in lists_and_dicts:
            if has(item, sub_data):
                return True
    return False


def subscription_schema(project, structure, level=0):
    """
    builds a schema from a list of nodes and events
    :param project: validation type
    :param structure: list of nodes (another list) and events
    :return: schema
    """
    sub_list = []
    for item in list_or_dict(structure):
        sub_list.append(subscription_schema(project, item, level=level+1))
    sub_list.append(event_schema(level))

    node_schema = {
        'node': {
            'id': Use(type(project._id), error="node_id{}".format(level)),
            'title': Use(type(project.title), error="node_title{}".format(level)),
            'url': Use(type(project.url), error="node_{}".format(level))
        },
        'kind': And(str, Use(lambda s: s in ('node', 'folder'), error="kind didn't match node or folder {}".format(level))),
        'nodeType': Use(lambda s: s in ('project', 'component'), error='nodeType not project or component'),
        'category': Use(lambda s: s in Node.CATEGORY_MAP, error='category not in Node.CATEGORY_MAP'),
        'permissions': {
            'view': Use(lambda s: s in (True, False), error='view permissions is not True/False')
        },
        'children': sub_list
    }
    if level == 0:
        return Schema([node_schema])
    return node_schema


def event_schema(level=None):
    return {
        'event': {
            'title': And(Use(str, error="event_title{} not a string".format(level)),
                         Use(lambda s: s in constants.NOTIFICATION_TYPES,
                             error="event_title{} not in list".format(level))),
            'description': And(Use(str, error="event_desc{} not a string".format(level)),
                               Use(lambda s: s in constants.NODE_SUBSCRIPTIONS_AVAILABLE,
                                   error="event_desc{} not in list".format(level))),
            'notificationType': And(str, Or('adopt_parent', lambda s: s in constants.NOTIFICATION_TYPES)),
            'parent_notification_type': Or(None, 'adopt_parent', lambda s: s in constants.NOTIFICATION_TYPES)
        },
        'kind': 'event',
        'children': And(list, lambda l: len(l) == 0)
    }


class TestNotificationUtils(OsfTestCase):
    def setUp(self):
        super(TestNotificationUtils, self).setUp()
        self.user = factories.UserFactory()
        self.project = factories.ProjectFactory(creator=self.user)
        self.project_subscription = factories.NotificationSubscriptionFactory(
            _id=self.project._id + '_' + 'comments',
            owner=self.project,
            event_name='comments'
        )
        self.project_subscription.save()
        self.project_subscription.email_transactional.append(self.user)
        self.project_subscription.save()

        self.node = factories.NodeFactory(parent=self.project, creator=self.user)
        self.node_subscription = factories.NotificationSubscriptionFactory(
            _id=self.node._id + '_' + 'comments',
            owner=self.node,
            event_name='comments'
        )
        self.node_subscription.save()
        self.node_subscription.email_transactional.append(self.user)
        self.node_subscription.save()

        self.user_subscription = factories.NotificationSubscriptionFactory(
            _id=self.user._id + '_' + 'comment_replies',
            owner=self.user,
            event_name='comment_replies'
        )
        self.user_subscription.save()
        self.user_subscription.email_transactional.append(self.user)
        self.user_subscription.save()

    def test_to_subscription_key(self):
        key = utils.to_subscription_key('xyz', 'comments')
        assert_equal(key, 'xyz_comments')

    def test_from_subscription_key(self):
        parsed_key = utils.from_subscription_key('xyz_comment_replies')
        assert_equal(parsed_key, {
            'uid': 'xyz',
            'event': 'comment_replies'
        })

    def test_get_all_user_subscriptions(self):
        user_subscriptions = [x for x in utils.get_all_user_subscriptions(self.user)]
        assert_in(self.project_subscription, user_subscriptions)
        assert_in(self.node_subscription, user_subscriptions)
        assert_in(self.user_subscription, user_subscriptions)
        assert_equal(len(user_subscriptions), 3)

    def test_get_all_node_subscriptions_given_user_subscriptions(self):
        user_subscriptions = utils.get_all_user_subscriptions(self.user)
        node_subscriptions = [x for x in utils.get_all_node_subscriptions(self.user, self.node, user_subscriptions=user_subscriptions)]
        assert_equal(node_subscriptions, [self.node_subscription])

    def test_get_all_node_subscriptions_given_user_and_node(self):
        node_subscriptions = [x for x in utils.get_all_node_subscriptions(self.user, self.node)]
        assert_equal(node_subscriptions, [self.node_subscription])

    def test_get_configured_project_ids_does_not_return_user_or_node_ids(self):
        configured_ids = utils.get_configured_projects(self.user)

        # No dupilcates!
        assert_equal(len(configured_ids), 1)

        assert_in(self.project._id, configured_ids)
        assert_not_in(self.node._id, configured_ids)
        assert_not_in(self.user._id, configured_ids)

    def test_get_configured_project_ids_excludes_deleted_projects(self):
        project = factories.ProjectFactory()
        subscription = factories.NotificationSubscriptionFactory(
            _id=project._id + '_' + 'comments',
            owner=project
        )
        subscription.save()
        subscription.email_transactional.append(self.user)
        subscription.save()
        project.is_deleted = True
        project.save()
        assert_not_in(project._id, utils.get_configured_projects(self.user))

    def test_get_configured_project_ids_excludes_node_with_project_category(self):
        node = factories.NodeFactory(parent=self.project, category='project')
        node_subscription = factories.NotificationSubscriptionFactory(
            _id=node._id + '_' + 'comments',
            owner=node,
            event_name='comments'
        )
        node_subscription.save()
        node_subscription.email_transactional.append(self.user)
        node_subscription.save()
        assert_not_in(node._id, utils.get_configured_projects(self.user))

    def test_get_configured_project_ids_includes_top_level_private_projects_if_subscriptions_on_node(self):
        private_project = factories.ProjectFactory()
        node = factories.NodeFactory(parent=private_project)
        node_subscription = factories.NotificationSubscriptionFactory(
            _id=node._id + '_comments',
            owner=node,
            event_name='comments'
        )
        node_subscription.email_transactional.append(node.creator)
        node_subscription.save()
        configured_project_ids = utils.get_configured_projects(node.creator)
        assert_in(private_project._id, configured_project_ids)

    def test_get_configured_project_ids_excludes_private_projects_if_no_subscriptions_on_node(self):
        private_project = factories.ProjectFactory()
        node = factories.NodeFactory(parent=private_project)
        configured_project_ids = utils.get_configured_projects(node.creator)
        assert_not_in(private_project._id, configured_project_ids)

    def test_get_parent_notification_type(self):
        nt = utils.get_parent_notification_type(self.node, 'comments', self.user)
        assert_equal(nt, 'email_transactional')

    def test_get_parent_notification_type_no_parent_subscriptions(self):
        node = factories.NodeFactory()
        nt = utils.get_parent_notification_type(node._id, 'comments', self.user)
        assert_equal(nt, None)

    def test_get_parent_notification_type_no_parent(self):
        project = factories.ProjectFactory()
        nt = utils.get_parent_notification_type(project._id, 'comments', self.user)
        assert_equal(nt, None)

    def test_get_parent_notification_type_handles_user_id(self):
        nt = utils.get_parent_notification_type(self.user._id, 'comments', self.user)
        assert_equal(nt, None)

    def test_format_data_project_settings(self):
        data = utils.format_data(self.user, [self.project._id])
        parent_event = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'email_transactional',
                'parent_notification_type': None
            },
            'kind': 'event',
            'children': []
        }
        child_event = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'email_transactional',
                'parent_notification_type': 'email_transactional'
            },
            'kind': 'event',
            'children': []
        }
        expected_new = [['event'], 'event']
        schema = subscription_schema(self.project, expected_new)
        assert schema.validate(data)
        assert has(data, parent_event)
        assert has(data, child_event)

    def test_format_data_node_settings(self):
        data = utils.format_data(self.user, [self.node._id])
        event = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'email_transactional',
                'parent_notification_type': 'email_transactional'
            },
            'kind': 'event',
            'children': []
        }
        schema = subscription_schema(self.project, ['event'])
        assert schema.validate(data)
        assert has(data, event)

    def test_format_includes_admin_view_only_component_subscriptions(self):
        """ Test private components in which parent project admins are not contributors still appear in their
            notifications settings.
        """
        node = factories.NodeFactory(parent=self.project)
        data = utils.format_data(self.user, [self.project._id])
        event = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'adopt_parent',
                'parent_notification_type': 'email_transactional'
            },
            'kind': 'event',
            'children': [],
        }
        schema = subscription_schema(self.project, ['event', ['event'], ['event']])
        assert schema.validate(data)
        assert has(data, event)

    def test_format_data_excludes_pointers(self):
        project = factories.ProjectFactory()
        subscription = factories.NotificationSubscriptionFactory(
            _id=project._id + '_comments',
            owner=project,
            event_name='comments'
        )
        subscription.email_transactional.append(project.creator)
        subscription.save()
        pointed = factories.ProjectFactory()
        project.add_pointer(pointed, Auth(project.creator))
        project.save()
        configured_project_ids = utils.get_configured_projects(project.creator)
        data = utils.format_data(project.creator, configured_project_ids)
        event = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'email_transactional',
                'parent_notification_type': None
            },
            'kind': 'event',
            'children': [],
        }
        schema = subscription_schema(self.project, ['event'])
        assert schema.validate(data)
        assert has(data, event)

    def test_format_data_user_subscriptions_includes_private_parent_if_configured_children(self):
        private_project = factories.ProjectFactory()
        node = factories.NodeFactory(parent=private_project)
        node_subscription = factories.NotificationSubscriptionFactory(
            _id=node._id + '_comments',
            owner=node,
            event_name='comments'
        )
        node_subscription.email_transactional.append(node.creator)
        node_subscription.save()
        configured_project_ids = utils.get_configured_projects(node.creator)
        data = utils.format_data(node.creator, configured_project_ids)
        event = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'email_transactional',
                'parent_notification_type': None
            },
            'kind': 'event',
            'children': [],
        }
        schema = subscription_schema(self.project, ['event', ['event']])
        assert schema.validate(data)
        assert has(data, event)

    def test_format_user_subscriptions(self):
        data = utils.format_user_subscriptions(self.user)
        expected = [{
            'event': {
                'title': 'comment_replies',
                'description': constants.USER_SUBSCRIPTIONS_AVAILABLE['comment_replies'],
                'notificationType': 'email_transactional',
                'parent_notification_type': None
            },
            'kind': 'event',
            'children': [],
        }]
        assert_equal(data, expected)

    def test_format_data_user_settings(self):
        data = utils.format_user_and_project_subscriptions(self.user)
        expected = [
            {
                'node': {
                    'id': self.user._id,
                    'title': 'User Notifications'
            },
                'kind': 'heading',
                'children': utils.format_user_subscriptions(self.user)
            },
            {
                'node': {
                    'id': '',
                    'title': 'Project Notifications'
                },
                'kind': 'heading',
                'children': utils.format_data(self.user, utils.get_configured_projects(self.user))
            }]

        assert_equal(data, expected)

    def test_serialize_user_level_event(self):
        user_subscriptions = [x for x in utils.get_all_user_subscriptions(self.user)]
        user_subscription = None
        for subscription in user_subscriptions:
            if 'comment_replies' in getattr(subscription, 'event_name'):
                user_subscription = subscription
        data = utils.serialize_event(self.user, event_description='comment_replies',
                                     subscription=user_subscription)
        expected = {
            'event': {
                'title': 'comment_replies',
                'description': constants.USER_SUBSCRIPTIONS_AVAILABLE['comment_replies'],
                'notificationType': 'email_transactional',
                'parent_notification_type': None
            },
            'kind': 'event',
            'children': []
        }
        assert_equal(data, expected)

    def test_serialize_node_level_event(self):
        node_subscriptions = [x for x in utils.get_all_node_subscriptions(self.user, self.node)]
        data = utils.serialize_event(user=self.user, event_description='comments',
                                     subscription=node_subscriptions[0], node=self.node)
        expected = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'email_transactional',
                'parent_notification_type': 'email_transactional'
            },
            'kind': 'event',
            'children': [],
        }
        assert_equal(data, expected)

    def test_serialize_node_level_event_that_adopts_parent_settings(self):
        user = factories.UserFactory()
        self.project.add_contributor(contributor=user, permissions=['read'])
        self.project.save()
        self.project_subscription.email_transactional.append(user)
        self.project_subscription.save()
        self.node.add_contributor(contributor=user, permissions=['read'])
        self.node.save()
        node_subscriptions = [x for x in utils.get_all_node_subscriptions(user, self.node)]
        data = utils.serialize_event(user=user, event_description='comments',
                                     subscription=node_subscriptions, node=self.node)
        expected = {
            'event': {
                'title': 'comments',
                'description': constants.NODE_SUBSCRIPTIONS_AVAILABLE['comments'],
                'notificationType': 'adopt_parent',
                'parent_notification_type': 'email_transactional'
            },
            'kind': 'event',
            'children': [],
        }
        assert_equal(data, expected)


class TestNotificationsDict(OsfTestCase):
    def test_notifications_dict_add_message_returns_proper_format(self):
        d = utils.NotificationsDict()
        message = {
            'message': 'Freddie commented on your project',
            'timestamp': datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        }
        message2 = {
            'message': 'Mercury commented on your component',
            'timestamp': datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        }

        d.add_message(['project'], message)
        d.add_message(['project', 'node'], message2)

        expected = {
            'messages': [],
            'children': collections.defaultdict(
                utils.NotificationsDict, {
                    'project': {
                        'messages': [message],
                        'children': collections.defaultdict(utils.NotificationsDict, {
                            'node': {
                                'messages': [message2],
                                'children': collections.defaultdict(utils.NotificationsDict, {})
                            }
                        })
                    }
                }
            )}
        assert_equal(d, expected)


class TestCompileSubscriptions(OsfTestCase):
    def setUp(self):
        super(TestCompileSubscriptions, self).setUp()
        self.user_1 = factories.UserFactory()
        self.user_2 = factories.UserFactory()
        self.user_3 = factories.UserFactory()
        self.user_4 = factories.UserFactory()
        # Base project + 1 project shared with 3 + 1 project shared with 2
        self.base_project = factories.ProjectFactory(is_public=False, creator=self.user_1)
        self.shared_node = factories.NodeFactory(parent=self.base_project, is_public=False, creator=self.user_1)
        self.private_node = factories.NodeFactory(parent=self.base_project, is_public=False, creator=self.user_1)
        # Adding contributors
        for node in [self.base_project, self.shared_node, self.private_node]:
            node.add_contributor(self.user_2, permissions='admin')
        self.base_project.add_contributor(self.user_3, permissions='write')
        self.shared_node.add_contributor(self.user_3, permissions='write')
        # Setting basic subscriptions
        self.base_sub = factories.NotificationSubscriptionFactory(
            _id=self.base_project._id + '_file_updated',
            owner=self.base_project,
            event_name='file_updated'
        )
        self.base_sub.save()
        self.shared_sub = factories.NotificationSubscriptionFactory(
            _id=self.shared_node._id + '_file_updated',
            owner=self.shared_node,
            event_name='file_updated'
        )
        self.shared_sub.save()
        self.private_sub = factories.NotificationSubscriptionFactory(
            _id=self.private_node._id + '_file_updated',
            owner=self.private_node,
            event_name='file_updated'
        )
        self.private_sub.save()

    def test_no_subscription(self):
        node = factories.NodeFactory()
        result = emails.compile_subscriptions(node, 'file_updated')
        assert_equal({'email_transactional': [], 'none': [], 'email_digest': []}, result)

    def test_no_subscribers(self):
        node = factories.NodeFactory()
        node_sub = factories.NotificationSubscriptionFactory(
            _id=node._id + '_file_updated',
            owner=node,
            event_name='file_updated'
        )
        node_sub.save()
        result = emails.compile_subscriptions(node, 'file_updated')
        assert_equal({'email_transactional': [], 'none': [], 'email_digest': []}, result)

    def test_creator_subbed_parent(self):
        """Basic sub check"""
        self.base_sub.email_transactional.append(self.user_1)
        self.base_sub.save()
        result = emails.compile_subscriptions(self.base_project, 'file_updated')
        assert_equal({'email_transactional': [self.user_1._id], 'none': [], 'email_digest': []}, result)

    def test_creator_subbed_to_parent_from_child(self):
        """checks the parent sub is the one to appear without a child sub"""
        self.base_sub.email_transactional.append(self.user_1)
        self.base_sub.save()
        result = emails.compile_subscriptions(self.shared_node, 'file_updated')
        assert_equal({'email_transactional': [self.user_1._id], 'none': [], 'email_digest': []}, result)

    def test_creator_subbed_to_both_from_child(self):
        """checks that only one sub is in the list."""
        self.base_sub.email_transactional.append(self.user_1)
        self.base_sub.save()
        self.shared_sub.email_transactional.append(self.user_1)
        self.shared_sub.save()
        result = emails.compile_subscriptions(self.shared_node, 'file_updated')
        assert_equal({'email_transactional': [self.user_1._id], 'none': [], 'email_digest': []}, result)

    def test_creator_diff_subs_to_both_from_child(self):
        """Check that the child node sub overrides the parent node sub"""
        self.base_sub.email_transactional.append(self.user_1)
        self.base_sub.save()
        self.shared_sub.none.append(self.user_1)
        self.shared_sub.save()
        result = emails.compile_subscriptions(self.shared_node, 'file_updated')
        assert_equal({'email_transactional': [], 'none': [self.user_1._id], 'email_digest': []}, result)

    def test_user_wo_permission_on_child_node_not_listed(self):
        """Tests to see if a user without permission gets an Email about a node they cannot see."""
        self.base_sub.email_transactional.append(self.user_3)
        self.base_sub.save()
        result = emails.compile_subscriptions(self.private_node, 'file_updated')
        assert_equal({'email_transactional': [], 'none': [], 'email_digest': []}, result)

    def test_several_nodes_deep(self):
        self.base_sub.email_transactional.append(self.user_1)
        self.base_sub.save()
        node2 = factories.NodeFactory(parent=self.shared_node)
        node3 = factories.NodeFactory(parent=node2)
        node4 = factories.NodeFactory(parent=node3)
        node5 = factories.NodeFactory(parent=node4)
        subs = emails.compile_subscriptions(node5, 'file_updated')
        assert_equal(subs, {'email_transactional': [self.user_1._id], 'email_digest': [], 'none': []})

    def test_several_nodes_deep_precedence(self):
        self.base_sub.email_transactional.append(self.user_1)
        self.base_sub.save()
        node2 = factories.NodeFactory(parent=self.shared_node)
        node3 = factories.NodeFactory(parent=node2)
        node4 = factories.NodeFactory(parent=node3)
        node4_subscription = factories.NotificationSubscriptionFactory(
            _id=node4._id + '_file_updated',
            owner=node4,
            event_name='file_updated'
        )
        node4_subscription.save()
        node4_subscription.email_digest.append(self.user_1)
        node4_subscription.save()
        node5 = factories.NodeFactory(parent=node4)
        subs = emails.compile_subscriptions(node5, 'file_updated')
        assert_equal(subs, {'email_transactional': [], 'email_digest': [self.user_1._id], 'none': []})

    def tearDown(self):
        pass


class TestMoveSubscription(OsfTestCase):
    def setUp(self):
        super(TestMoveSubscription, self).setUp()
        self.user_1 = factories.AuthUserFactory()
        self.auth = Auth(user=self.user_1)
        self.user_2 = factories.AuthUserFactory()
        self.user_3 = factories.AuthUserFactory()
        self.user_4 = factories.AuthUserFactory()
        self.project = factories.ProjectFactory(creator=self.user_1)
        self.private_node = factories.NodeFactory(parent=self.project, is_public=False, creator=self.user_1)
        self.sub = factories.NotificationSubscriptionFactory(
            _id=self.project._id + '_file_updated',
            owner=self.project,
            event_name='file_updated'
        )
        self.sub.email_transactional.extend([self.user_1])
        self.sub.save()
        self.file_sub = factories.NotificationSubscriptionFactory(
            _id=self.project._id + '_xyz42_file_updated',
            owner=self.project,
            event_name='xyz42_file_updated'
        )
        self.file_sub.save()

    @mock.patch('website.notifications.emails.notify')
    def test_removed_users_notified(self, mock_notify):
        time_now = datetime.datetime.utcnow()
        recipients = {'email_transactional': [self.user_2, self.user_3], 'email_digest': [], 'none': []}
        emails.warn_users_removed_from_subscription(recipients, 'xyz42_file_updated', self.user_1,
                                                    self.project, time_now)
        mock_notify.assert_called_with(self.project._id, 'xyz42_file_updated', self.user_1, self.project, time_now)

    @mock.patch('website.notifications.emails.notify')
    def test_no_removed_users_to_notify(self, mock_notify):
        time_now = datetime.datetime.utcnow()
        recipients = {}
        emails.warn_users_removed_from_subscription(recipients, 'xyz42_file_updated', self.user_1,
                                                    self.project, time_now)
        assert_false(mock_notify.called)

    @mock.patch('website.notifications.emails.notify')
    def test_old_sub_removed(self, mock_notify):
        time_now = datetime.datetime.utcnow()
        utils.move_subscription('xyz42_file_updated', self.project, 'abc42_file_updated', self.private_node)
        recipients = {'email_transactional': [self.user_2, self.user_3], 'email_digest': [], 'none': []}
        emails.warn_users_removed_from_subscription(recipients, 'xyz42_file_updated', self.user_1,
                                                    self.project, time_now)
        mock_notify.assert_called_with(self.project._id, 'xyz42_file_updated', self.user_1, self.project, time_now)

    def test_event_subs_same(self):
        self.file_sub.email_transactional.extend([self.user_2, self.user_3, self.user_4])
        self.file_sub.save()
        self.private_node.add_contributor(self.user_2, permissions=['admin', 'write', 'read'], auth=self.auth)
        self.private_node.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.private_node.save()
        results = utils.move_subscription('xyz42_file_updated', self.project, 'xyz42_file_updated', self.private_node)
        assert_equal({}, results)

    def test_event_nodes_same(self):
        self.file_sub.email_transactional.extend([self.user_2, self.user_3, self.user_4])
        self.file_sub.save()
        self.private_node.add_contributor(self.user_2, permissions=['admin', 'write', 'read'], auth=self.auth)
        self.private_node.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.private_node.save()
        results = utils.move_subscription('xyz42_file_updated', self.project, 'abc42_file_updated', self.project)
        assert_equal({}, results)

    def test_move_sub(self):
        """Tests old sub is replaced with new sub."""
        utils.move_subscription('xyz42_file_updated', self.project, 'abc42_file_updated', self.private_node)
        assert_equal('abc42_file_updated', self.file_sub.event_name)
        assert_equal(self.private_node, self.file_sub.owner)
        assert_equal(self.private_node._id + '_abc42_file_updated', self.file_sub._id)

    def test_remove_one_user(self):
        """One user doesn't have permissions on the node the sub is moved to. Should be listed."""
        self.file_sub.email_transactional.extend([self.user_2, self.user_3, self.user_4])
        self.file_sub.save()
        self.private_node.add_contributor(self.user_2, permissions=['admin', 'write', 'read'], auth=self.auth)
        self.private_node.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.private_node.save()
        results = utils.move_subscription('xyz42_file_updated', self.project, 'abc42_file_updated', self.private_node)
        assert_equal({'email_transactional': [self.user_4], 'email_digest': []}, results)

        # url = self.private_node.api_url_for('get_contributors')
        # res = self.app.get(url, auth=self.user_1.auth)
        # result = [item['id'] for item in res.json['contributors']]
        # print result

    def test_remove_one_user_warn_another(self):
        """Two users do not have permissions on new node, but one has a project sub. Both should be listed."""
        self.private_node.add_contributor(self.user_2, permissions=['admin', 'write', 'read'], auth=self.auth)
        self.private_node.save()
        self.project.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.project.save()
        self.sub.email_digest.append(self.user_3)
        self.sub.save()
        self.file_sub.email_transactional.extend([self.user_2, self.user_4])
        results = utils.move_subscription('xyz42_file_updated', self.project, 'abc42_file_updated', self.private_node)
        assert_equal({'email_transactional': [self.user_4], 'email_digest': [self.user_3]}, results)
        assert_in(self.user_3, self.sub.email_digest)  # Is not removed from the project subscription.

    def test_warn_user(self):
        """One user with a project sub does not have permission on new node. User should be listed."""
        self.private_node.add_contributor(self.user_2, permissions=['admin', 'write', 'read'], auth=self.auth)
        self.private_node.save()
        self.project.add_contributor(self.user_3, permissions=['write', 'read'], auth=self.auth)
        self.project.save()
        self.sub.email_digest.append(self.user_3)
        self.sub.save()
        self.file_sub.email_transactional.extend([self.user_2])
        results = utils.move_subscription('xyz42_file_updated', self.project, 'abc42_file_updated', self.private_node)
        assert_equal({'email_transactional': [], 'email_digest': [self.user_3]}, results)
        assert_in(self.user_3, self.sub.email_digest)  # Is not removed from the project subscription.


class TestSendEmails(OsfTestCase):
    def setUp(self):
        super(TestSendEmails, self).setUp()
        self.user = factories.UserFactory()
        self.project = factories.ProjectFactory()
        self.project_subscription = factories.NotificationSubscriptionFactory(
            _id=self.project._id + '_' + 'comments',
            owner=self.project,
            event_name='comments'
        )
        self.project_subscription.save()
        self.project_subscription.email_transactional.append(self.project.creator)
        self.project_subscription.save()

        self.node = factories.NodeFactory(parent=self.project)
        self.node_subscription = factories.NotificationSubscriptionFactory(
            _id=self.node._id + '_comments',
            owner=self.node,
            event_name='comments'
        )
        self.node_subscription.save()

    @mock.patch('website.notifications.emails.send')
    def test_notify_no_subscription(self, send):
        node = factories.NodeFactory()
        emails.notify(node._id, 'comments', user=self.user, node=node, timestamp=datetime.datetime.utcnow())
        assert_false(send.called)

    @mock.patch('website.notifications.emails.send')
    def test_notify_no_subscribers(self, send):
        node = factories.NodeFactory()
        node_subscription = factories.NotificationSubscriptionFactory(
            _id=node._id + '_comments',
            owner=node,
            event_name='comments'
        )
        node_subscription.save()
        emails.notify(node._id, 'comments', user=self.user, node=node, timestamp=datetime.datetime.utcnow())
        assert_false(send.called)

    @mock.patch('website.notifications.emails.send')
    def test_notify_sends_with_correct_args(self, send):
        time_now = datetime.datetime.utcnow()
        emails.notify(self.project._id, 'comments', user=self.user, node=self.node, timestamp=time_now)
        assert_true(send.called)
        send.assert_called_with([self.project.creator._id], 'email_transactional', self.project._id, 'comments',
                                self.user, self.node, time_now)

    @mock.patch('website.notifications.emails.send')
    def test_notify_does_not_send_to_users_subscribed_to_none(self, send):
        node = factories.NodeFactory()
        user = factories.UserFactory()
        node_subscription = factories.NotificationSubscriptionFactory(
            _id=node._id + '_comments',
            owner=node,
            event_name='comments'
        )
        node_subscription.save()
        node_subscription.none.append(user)
        node_subscription.save()
        sent = emails.notify(node._id, 'comments', user=user, node=node, timestamp=datetime.datetime.utcnow())
        assert_false(send.called)
        assert_equal(sent, [])

    @mock.patch('website.notifications.emails.send')
    def test_notify_sends_comment_reply_event_if_comment_is_direct_reply(self, mock_send):
        time_now = datetime.datetime.utcnow()
        sent_subscribers = emails.notify(self.project._id, 'comments', user=self.user, node=self.node,
                                         timestamp=time_now, target_user=self.project.creator)
        mock_send.assert_called_with([self.project.creator._id], 'email_transactional', self.project._id,
                                     'comment_replies', self.user, self.node, time_now,
                                     target_user=self.project.creator)

    @mock.patch('website.notifications.emails.send')
    def test_notify_sends_comment_event_if_comment_reply_is_not_direct_reply(self, mock_send):
        user = factories.UserFactory()
        time_now = datetime.datetime.utcnow()
        sent_subscribers = emails.notify(self.project._id, 'comments', user=user, node=self.node, timestamp=time_now,
                                         target_user=user)
        mock_send.assert_called_with([self.project.creator._id], 'email_transactional', self.project._id,
                                     'comments', user, self.node, time_now, target_user=user)

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.notifications.emails.send')
    def test_notify_does_not_send_comment_if_they_reply_to_their_own_comment(self, mock_send, mock_send_mail):
        user = factories.UserFactory()
        time_now = datetime.datetime.utcnow()
        sent_subscribers = emails.notify(self.project._id, 'comments', user=self.project.creator, node=self.project,
                                         timestamp=time_now,  target_user=self.project.creator)
        assert_false(mock_send.called)
        assert_false(mock_send_mail.called)

    @mock.patch('website.notifications.emails.send')
    def test_notify_sends_comment_event_if_comment_reply_is_not_direct_reply_on_component(self, mock_send):
        """ Test that comment replies on components that are not direct replies to the subscriber use the
            "comments" email template.
        """
        user = factories.UserFactory()
        time_now = datetime.datetime.utcnow()
        sent_subscribers = emails.notify(self.node._id, 'comments', user, self.node,
                                         time_now, target_user=user)
        mock_send.assert_called_with([self.project.creator._id], 'email_transactional', self.node._id, 'comments',
                                     user, self.node, time_now, target_user=user)

    def test_check_node_node_none(self):
        subs = emails.check_node(None, 'comments')
        assert_equal(subs, {'email_transactional': [], 'email_digest': [], 'none': []})

    def test_check_node_one(self):
        subs = emails.check_node(self.project, 'comments')
        assert_equal(subs, {'email_transactional': [self.project.creator._id], 'email_digest': [], 'none': []})

    @mock.patch('website.project.views.comment.notify')
    def test_check_user_comment_reply_subscription_if_email_not_sent_to_target_user(self, mock_notify):
        # user subscribed to comment replies
        user = factories.UserFactory()
        user_subscription = factories.NotificationSubscriptionFactory(
            _id=user._id + '_comments',
            owner=user,
            event_name='comment_replies'
        )
        user_subscription.email_transactional.append(user)
        user_subscription.save()

        # user is not subscribed to project comment notifications
        project = factories.ProjectFactory()

        # reply to user
        target = factories.CommentFactory(node=project, user=user)
        content = 'hammer to fall'

        # auth=project.creator.auth
        url = project.api_url + 'comment/'
        self.app.post_json(
            url,
            {
                'content': content,
                'isPublic': 'public',
                'target': target._id

            },
            auth=project.creator.auth
        )
        assert_true(mock_notify.called)
        assert_equal(mock_notify.call_count, 2)

    # @mock.patch('website.notifications.emails.email_transactional')
    # def test_send_calls_correct_mail_function(self, email_transactional):
    #     emails.send([self.user], 'email_transactional', self.project._id, 'comments',
    #                 timestamp=datetime.datetime.utcnow(),
    #                 user=self.project.creator,
    #                 gravatar_url=self.user.gravatar_url,
    #                 content='',
    #                 parent_comment='',
    #                 title=self.project.title,
    #                 url=self.project.absolute_url
    #     )
    #     assert_true(email_transactional.called)

    @mock.patch('website.mails.send_mail')
    def test_send_email_transactional(self, send_mail):
        # assert that send_mail is called with the correct person & args
        subscribed_users = [self.user._id]
        timestamp = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)

        emails.email_transactional(
            subscribed_users, self.project._id, 'comments',
            user=self.project.creator,
            node=self.project,
            timestamp=timestamp,
            gravatar_url=self.user.gravatar_url,
            content='',
            parent_comment='',
            title=self.project.title,
            url=self.project.absolute_url,
        )
        subject = Template(constants.EMAIL_SUBJECT_MAP['comments']).render(
            timestamp=timestamp,
            user=self.project.creator,
            gravatar_url=self.user.gravatar_url,
            content='',
            parent_comment='',
            title=self.project.title,
            url=self.project.absolute_url,
        )
        message = mails.render_message(
            'comments.html.mako',
            timestamp=timestamp,
            user=self.project.creator,
            gravatar_url=self.user.gravatar_url,
            content='',
            parent_comment='',
            title=self.project.title,
            url=self.project.absolute_url,
            localized_timestamp=emails.localize_timestamp(timestamp, self.user),
        )

        assert_true(send_mail.called)
        send_mail.assert_called_with(
            to_addr=self.user.username,
            mail=mails.TRANSACTIONAL,
            mimetype='html',
            name=self.user.fullname,
            node_title=self.project.title,
            node_id=self.project._id,
            subject=subject,
            message=message,
            url=self.project.absolute_url + 'settings/',
        )

    def test_send_email_digest_creates_digest_notification(self):
        subscribed_users = [factories.UserFactory()._id]
        digest_count_before = NotificationDigest.find().count()
        emails.email_digest(subscribed_users, self.project._id, 'comments',
                            user=self.user,
                            node=self.project,
                            timestamp=datetime.datetime.utcnow().replace(tzinfo=pytz.utc),
                            gravatar_url=self.user.gravatar_url,
                            content='',
                            parent_comment='',
                            title=self.project.title,
                            url=self.project.absolute_url
        )
        digest_count = NotificationDigest.find().count()
        assert_equal((digest_count - digest_count_before), 1)

    def test_get_settings_url_for_node(self):
        url = emails.get_settings_url(self.project._id, self.user)
        assert_equal(url, self.project.absolute_url + 'settings/')

    def test_get_settings_url_for_user(self):
        url = emails.get_settings_url(self.user._id, self.user)
        assert_equal(url, web_url_for('user_notifications', _absolute=True))

    def test_get_node_lineage(self):
        node_lineage = emails.get_node_lineage(self.node)
        assert_equal(node_lineage, [self.project._id, self.node._id])

    def test_localize_timestamp(self):
        timestamp = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        self.user.timezone = 'America/New_York'
        self.user.locale = 'en_US'
        self.user.save()
        tz = dates.get_timezone(self.user.timezone)
        locale = Locale(self.user.locale)
        formatted_date = dates.format_date(timestamp, format='full', locale=locale)
        formatted_time = dates.format_time(timestamp, format='short', tzinfo=tz, locale=locale)
        formatted_datetime = u'{time} on {date}'.format(time=formatted_time, date=formatted_date)
        assert_equal(emails.localize_timestamp(timestamp, self.user), formatted_datetime)

    def test_localize_timestamp_empty_timezone(self):
        timestamp = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        self.user.timezone = ''
        self.user.locale = 'en_US'
        self.user.save()
        tz = dates.get_timezone('Etc/UTC')
        locale = Locale(self.user.locale)
        formatted_date = dates.format_date(timestamp, format='full', locale=locale)
        formatted_time = dates.format_time(timestamp, format='short', tzinfo=tz, locale=locale)
        formatted_datetime = u'{time} on {date}'.format(time=formatted_time, date=formatted_date)
        assert_equal(emails.localize_timestamp(timestamp, self.user), formatted_datetime)

    def test_localize_timestamp_empty_locale(self):
        timestamp = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        self.user.timezone = 'America/New_York'
        self.user.locale = ''
        self.user.save()
        tz = dates.get_timezone(self.user.timezone)
        locale = Locale('en')
        formatted_date = dates.format_date(timestamp, format='full', locale=locale)
        formatted_time = dates.format_time(timestamp, format='short', tzinfo=tz, locale=locale)
        formatted_datetime = u'{time} on {date}'.format(time=formatted_time, date=formatted_date)
        assert_equal(emails.localize_timestamp(timestamp, self.user), formatted_datetime)

    def test_localize_timestamp_handles_unicode(self):
        timestamp = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        self.user.timezone = 'Europe/Moscow'
        self.user.locale = 'ru_RU'
        self.user.save()
        tz = dates.get_timezone(self.user.timezone)
        locale = Locale(self.user.locale)
        formatted_date = dates.format_date(timestamp, format='full', locale=locale)
        formatted_time = dates.format_time(timestamp, format='short', tzinfo=tz, locale=locale)
        formatted_datetime = u'{time} on {date}'.format(time=formatted_time, date=formatted_date)
        assert_equal(emails.localize_timestamp(timestamp, self.user), formatted_datetime)


class TestSendDigest(OsfTestCase):
    def test_group_digest_notifications_by_user(self):
        user = factories.UserFactory()
        user2 = factories.UserFactory()
        project = factories.ProjectFactory()
        timestamp = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).replace(microsecond=0)
        d = factories.NotificationDigestFactory(
            user_id=user._id,
            timestamp=timestamp,
            message='Hello',
            node_lineage=[project._id]
        )
        d.save()
        d2 = factories.NotificationDigestFactory(
            user_id=user2._id,
            timestamp=timestamp,
            message='Hello',
            node_lineage=[project._id]
        )
        d2.save()
        user_groups = group_digest_notifications_by_user()
        expected = [{
                    u'user_id': user._id,
                    u'info': [{
                        u'message': u'Hello',
                        u'node_lineage': [unicode(project._id)],
                        u'_id': d._id
                    }]
                    },
                    {
                    u'user_id': user2._id,
                    u'info': [{
                        u'message': u'Hello',
                        u'node_lineage': [unicode(project._id)],
                        u'_id': d2._id
                    }]
        }]

        assert_equal(len(user_groups), 2)
        assert_equal(user_groups, expected)

    @mock.patch('scripts.send_digest.remove_sent_digest_notifications')
    @mock.patch('website.mails.send_mail')
    def test_send_digest_called_with_correct_args(self, mock_send_mail, mock_callback):
        d = factories.NotificationDigestFactory(
            user_id=factories.UserFactory()._id,
            timestamp=datetime.datetime.utcnow(),
            message='Hello',
            node_lineage=[factories.ProjectFactory()._id]
        )
        d.save()
        user_groups = group_digest_notifications_by_user()
        send_digest(user_groups)
        assert_true(mock_send_mail.called)
        assert_equals(mock_send_mail.call_count, len(user_groups))

        last_user_index = len(user_groups) - 1
        user = User.load(user_groups[last_user_index]['user_id'])
        digest_notification_ids = [message['_id'] for message in user_groups[last_user_index]['info']]

        args, kwargs = mock_send_mail.call_args

        assert_equal(kwargs['to_addr'], user.username)
        assert_equal(kwargs['mimetype'], 'html')
        assert_equal(kwargs['mail'], mails.DIGEST)
        assert_equal(kwargs['name'], user.fullname)
        message = group_messages_by_node(user_groups[last_user_index]['info'])
        assert_equal(kwargs['message'], message)
        assert_equal(kwargs['callback'],
                mock_callback.si(digest_notification_ids=digest_notification_ids))

    def test_remove_sent_digest_notifications(self):
        d = factories.NotificationDigestFactory(
            user_id=factories.UserFactory()._id,
            timestamp=datetime.datetime.utcnow(),
            message='Hello',
            node_lineage=[factories.ProjectFactory()._id]
        )
        digest_id = d._id
        remove_sent_digest_notifications(digest_notification_ids=[digest_id])
        with assert_raises(NoResultsFound):
            NotificationDigest.find_one(Q('_id', 'eq', digest_id))
