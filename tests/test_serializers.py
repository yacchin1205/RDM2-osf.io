# -*- coding: utf-8 -*-

from unittest import mock
import datetime as dt

from osf.models.mapcore_group import MapCoreGroup
from osf.models.mapcore_node_group import MapCoreNodeGroup
from django.contrib.auth.models import Group as AuthGroup
import pytest
from osf_tests.factories import (
    ProjectFactory,
    UserFactory,
    RegistrationFactory,
    NodeFactory,
    OSFGroupFactory,
    CollectionFactory,
)
from osf.models import NodeRelation, UserQuota
from osf.utils import permissions
from tests.base import OsfTestCase, get_default_metaschema

from framework.auth import Auth
from website.project.views.node import _view_project, _serialize_node_search, _get_children, _get_readable_descendants
from website.views import serialize_node_summary, serialize_mapcore_group_for_summary
from website.profile import utils
from website import filters, settings

pytestmark = pytest.mark.django_db

@pytest.mark.enable_bookmark_creation
@pytest.mark.enable_quickfiles_creation
class TestUserSerializers(OsfTestCase):
    def test_serialize_user(self):
        master = UserFactory()
        user = UserFactory()
        master.merge_user(user)
        d = utils.serialize_user(user)
        assert (d['id']) == (user._primary_key)
        assert (d['url']) == (user.url)
        assert (d.get('username', None)) == (None)
        assert (d['fullname']) == (user.fullname)
        assert (d['registered']) == (user.is_registered)
        assert (d['absolute_url']) == (user.absolute_url)
        assert (d['date_registered']) == (user.date_registered.strftime('%Y-%m-%d'))
        assert (d['active']) == (user.is_active)

    def test_serialize_user_merged(self):
        master = UserFactory()
        user = UserFactory()
        master.merge_user(user)
        d = utils.serialize_user(user, full=True)
        assert (d['is_merged'])
        assert (d['merged_by']['url']) == (user.merged_by.url)
        assert (d['merged_by']['absolute_url']) == (user.merged_by.absolute_url)

    def test_serialize_user_full(self):
        user = UserFactory()
        project = ProjectFactory(creator=user, is_public=False)
        NodeFactory(creator=user)
        ProjectFactory(creator=user, is_public=True)
        CollectionFactory(creator=user)
        RegistrationFactory(project=project)
        d = utils.serialize_user(user, full=True, include_node_counts=True)
        profile_image_url = filters.profile_image_url(settings.PROFILE_IMAGE_PROVIDER,
                                                  user,
                                                  use_ssl=True,
                                                  size=settings.PROFILE_IMAGE_LARGE)
        assert (d['id']) == (user._primary_key)
        assert (d['url']) == (user.url)
        assert (d.get('username')) == (None)
        assert (d['fullname']) == (user.fullname)
        assert (d['registered']) == (user.is_registered)
        assert (d['profile_image_url']) == (profile_image_url)
        assert (d['absolute_url']) == (user.absolute_url)
        assert (d['date_registered']) == (user.date_registered.strftime('%Y-%m-%d'))
        projects = [
            node
            for node in user.contributed
            if node.category == 'project'
            and not node.is_registration
            and not node.is_deleted
        ]
        public_projects = [p for p in projects if p.is_public]
        assert (d['number_projects']) == (len(projects))
        assert (d['number_public_projects']) == (len(public_projects))

    def test_serialize_user_max_quota_zero(self):
        user = UserFactory()
        NodeFactory(creator=user)
        ProjectFactory(creator=user, is_public=True)
        UserQuota.objects.create(
            user=user,
            storage_type=UserQuota.NII_STORAGE,
            max_quota=0,
            used=75
        )
        d = utils.serialize_user(user, full=True)
        assert (d['id']) == (user._primary_key)
        assert (d['url']) == (user.url)
        assert (d.get('username')) == (None)
        assert (d['fullname']) == (user.fullname)
        assert (d.get('quota')) is not None
        assert (d.get('quota', None)['rate']) == ('100.0')


@pytest.mark.enable_bookmark_creation
class TestNodeSerializers(OsfTestCase):

    # Regression test for #489
    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/489
    def test_serialize_node_summary_private_node_should_include_id_and_primary_boolean_reg_and_fork(self):
        user = UserFactory()
        # user cannot see this node
        node = ProjectFactory(is_public=False)
        result = serialize_node_summary(
            node, auth=Auth(user),
            primary=True,
        )

        # serialized result should have id and primary
        assert (result['id']) == (node._primary_key)
        assert (result['primary']), (True)
        assert (result['is_registration']) == (node.is_registration)
        assert (result['is_fork']) == (node.is_fork)

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/668
    def test_serialize_node_summary_for_registration_uses_correct_date_format(self):
        reg = RegistrationFactory()
        res = serialize_node_summary(reg, auth=Auth(reg.creator))
        assert (res['registered_date']) == (reg.registered_date.strftime('%Y-%m-%d %H:%M UTC'))

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/858
    def test_serialize_node_summary_private_registration_should_include_is_registration(self):
        user = UserFactory()
        # non-contributor cannot see private registration of public project
        node = ProjectFactory(is_public=True)
        reg = RegistrationFactory(project=node, user=node.creator)
        res = serialize_node_summary(reg, auth=Auth(user))

        # serialized result should have is_registration
        assert (res['is_registration'])

    # https://openscience.atlassian.net/browse/OSF-4618
    def test_get_children_only_returns_child_nodes_with_admin_permissions(self):
        user = UserFactory()
        admin_project = ProjectFactory()
        admin_project.add_contributor(user, auth=Auth(admin_project.creator),
                                      permissions=permissions.ADMIN)
        admin_project.save()

        admin_component = NodeFactory(parent=admin_project)
        admin_component.add_contributor(user, auth=Auth(admin_component.creator),
                                        permissions=permissions.ADMIN)
        admin_component.save()

        read_and_write = NodeFactory(parent=admin_project)
        read_and_write.add_contributor(user, auth=Auth(read_and_write.creator),
                                       permissions=permissions.WRITE)
        read_and_write.save()
        read_only = NodeFactory(parent=admin_project)
        read_only.add_contributor(user, auth=Auth(read_only.creator),
                                  permissions=permissions.READ)
        read_only.save()

        non_contributor = NodeFactory(parent=admin_project)
        components = _get_children(admin_project, Auth(user))
        assert (len(components)) == (1)

    def test_serialize_node_summary_private_fork_should_include_is_fork(self):
        user = UserFactory()
        # non-contributor cannot see private fork of public project
        node = ProjectFactory(is_public=True)
        consolidated_auth = Auth(user=node.creator)
        fork = node.fork_node(consolidated_auth)

        res = serialize_node_summary(
            fork, auth=Auth(user),
            primary=True,
        )
        # serialized result should have is_fork
        assert (res['is_fork'])

    def test_serialize_node_summary_private_fork_private_project_should_include_is_fork(self):
        # contributor on a private project
        user = UserFactory()
        node = ProjectFactory(is_public=False)
        node.add_contributor(user)

        # contributor cannot see private fork of this project
        consolidated_auth = Auth(user=node.creator)
        fork = node.fork_node(consolidated_auth)

        res = serialize_node_summary(
            fork, auth=Auth(user),
            primary=True,
        )
        # serialized result should have is_fork
        assert not (res['can_view'])
        assert (res['is_fork'])

    def test_serialize_node_summary_child_exists(self):
        user = UserFactory()
        parent_node = ProjectFactory(creator=user)
        linked_node = ProjectFactory(creator=user)
        result = _view_project(parent_node, Auth(user))
        assert (result['node']['child_exists']) == (False)
        parent_node.add_node_link(linked_node, Auth(user), save=True)
        result = _view_project(parent_node, Auth(user))
        assert (result['node']['child_exists']) == (False)
        child_component = NodeFactory(creator=user, parent=parent_node)
        result = _view_project(parent_node, Auth(user))
        assert (result['node']['child_exists']) == (True)

    def test_serialize_node_summary_is_contributor_osf_group(self):
        project = ProjectFactory()
        user = UserFactory()
        group = OSFGroupFactory(creator=user)
        project.add_osf_group(group, permissions.WRITE)

        res = _view_project(
            project, auth=Auth(user),
        )
        assert not (res['user']['is_contributor'])
        assert (res['user']['is_contributor_or_group_member'])
        assert not (res['user']['is_admin'])
        assert (res['user']['can_edit'])
        assert (res['user']['has_read_permissions'])
        assert (set(res['user']['permissions'])) == (set([permissions.READ, permissions.WRITE]))
        assert (res['user']['can_comment'])

    def test_serialize_node_search_returns_only_visible_contributors(self):
        node = NodeFactory()
        non_visible_contributor = UserFactory()
        node.add_contributor(non_visible_contributor, visible=False)
        serialized_node = _serialize_node_search(node)

        assert (serialized_node['firstAuthor']) == (node.visible_contributors[0].family_name)
        assert (len(node.visible_contributors)) == (1)
        assert not (serialized_node['etal'])


@pytest.mark.enable_bookmark_creation
class TestViewProject(OsfTestCase):

    def setUp(self):
        super(TestViewProject, self).setUp()
        self.user = UserFactory()
        self.node = ProjectFactory(creator=self.user)

    def test_view_project_pending_registration_for_admin_contributor_does_contain_cancel_link(self):
        pending_reg = RegistrationFactory(project=self.node, archive=True)
        assert (pending_reg.is_pending_registration)
        result = _view_project(pending_reg, Auth(self.user))

        assert (result['node']['disapproval_link']) != ('')
        assert ('/?token=') in (result['node']['disapproval_link'])
        pending_reg.delete()

    def test_view_project_pending_registration_for_write_contributor_does_not_contain_cancel_link(self):
        write_user = UserFactory()
        self.node.add_contributor(write_user, permissions=permissions.WRITE,
                                  auth=Auth(self.user), save=True)
        pending_reg = RegistrationFactory(project=self.node, archive=True)
        assert (pending_reg.is_pending_registration)
        result = _view_project(pending_reg, Auth(write_user))

        assert (result['node']['disapproval_link']) == ('')
        pending_reg.delete()

    def test_view_project_child_exists(self):
        linked_node = ProjectFactory(creator=self.user)
        result = _view_project(self.node, Auth(self.user))
        assert (result['node']['child_exists']) == (False)
        self.node.add_node_link(linked_node, Auth(self.user), save=True)
        result = _view_project(self.node, Auth(self.user))
        assert (result['node']['child_exists']) == (False)
        child_component = NodeFactory(creator=self.user, parent=self.node)
        result = _view_project(self.node, Auth(self.user))
        assert (result['node']['child_exists']) == (True)



@pytest.mark.enable_bookmark_creation
class TestViewProjectEmbeds(OsfTestCase):

    def setUp(self):
        super(TestViewProjectEmbeds, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)

    def test_view_project_embed_forks_excludes_registrations(self):
        project = ProjectFactory()
        fork = project.fork_node(Auth(project.creator))
        reg = RegistrationFactory(project=fork)

        res = _view_project(project, auth=Auth(project.creator), embed_forks=True)

        assert ('forks') in (res['node'])
        assert (len(res['node']['forks'])) == (1)

        assert (res['node']['forks'][0]['id']) == (fork._id)

    # Regression test
    def test_view_project_embed_registrations_sorted_by_registered_date_descending(self):
        # register a project several times, with various registered_dates
        registrations = []
        for days_ago in (21, 3, 2, 8, 13, 5, 1):
            registration = RegistrationFactory(project=self.project)
            reg_date = registration.registered_date - dt.timedelta(days_ago)
            registration.registered_date = reg_date
            registration.save()
            registrations.append(registration)

        registrations.sort(key=lambda r: r.registered_date, reverse=True)
        expected = [r._id for r in registrations]

        data = _view_project(node=self.project, auth=Auth(self.project.creator), embed_registrations=True)
        actual = [n['id'] for n in data['node']['registrations']]
        assert (actual) == (expected)

    def test_view_project_embed_descendants(self):
        child = NodeFactory(parent=self.project, creator=self.user)
        res = _view_project(self.project, auth=Auth(self.project.creator), embed_descendants=True)
        assert ('descendants') in (res['node'])
        assert (len(res['node']['descendants'])) == (1)
        assert (res['node']['descendants'][0]['id']) == (child._id)


class TestGetReadableDescendants(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = UserFactory()

    def test__get_readable_descendants(self):
        project = ProjectFactory(creator=self.user)
        child = NodeFactory(parent=project, creator=self.user)
        nodes, all_readable = _get_readable_descendants(auth=Auth(project.creator), node=project)
        assert (nodes[0]._id) == (child._id)
        assert (all_readable)

    def test__get_readable_descendants_includes_pointers(self):
        project = ProjectFactory(creator=self.user)
        pointed = ProjectFactory()
        node_relation = project.add_pointer(pointed, auth=Auth(self.user))
        project.save()

        nodes, all_readable = _get_readable_descendants(auth=Auth(project.creator), node=project)

        assert (len(nodes)) == (1)
        assert (nodes[0].title) == (pointed.title)
        assert (nodes[0]._id) == (pointed._id)
        assert (all_readable)

    def test__get_readable_descendants_masked_by_permissions(self):
        # Users should be able to see through components they do not have
        # permissions to.
        # Users should not be able to see through links to nodes they do not
        # have permissions to.
        #
        #                   1(AB)
        #                  /  |  \
        #                 *   |   \
        #                /    |    \
        #             2(A)  4(B)    7(A)
        #               |     |     |    \
        #               |     |     |     \
        #             3(AB) 5(B)    8(AB) 9(B)
        #                     |
        #                     |
        #                   6(A)
        #
        #
        userA = UserFactory(fullname='User A')
        userB = UserFactory(fullname='User B')

        project1 = ProjectFactory(creator=self.user, title='One')
        project1.add_contributor(userA, auth=Auth(self.user), permissions=permissions.READ)
        project1.add_contributor(userB, auth=Auth(self.user), permissions=permissions.READ)

        component2 = ProjectFactory(creator=self.user, title='Two')
        component2.add_contributor(userA, auth=Auth(self.user), permissions=permissions.READ)

        component3 = ProjectFactory(creator=self.user, title='Three')
        component3.add_contributor(userA, auth=Auth(self.user), permissions=permissions.READ)
        component3.add_contributor(userB, auth=Auth(self.user), permissions=permissions.READ)

        component4 = ProjectFactory(creator=self.user, title='Four')
        component4.add_contributor(userB, auth=Auth(self.user), permissions=permissions.READ)

        component5 = ProjectFactory(creator=self.user, title='Five')
        component5.add_contributor(userB, auth=Auth(self.user), permissions=permissions.READ)

        component6 = ProjectFactory(creator=self.user, title='Six')
        component6.add_contributor(userA, auth=Auth(self.user), permissions=permissions.READ)

        component7 = ProjectFactory(creator=self.user, title='Seven')
        component7.add_contributor(userA, auth=Auth(self.user), permissions=permissions.READ)

        component8 = ProjectFactory(creator=self.user, title='Eight')
        component8.add_contributor(userA, auth=Auth(self.user), permissions=permissions.READ)
        component8.add_contributor(userB, auth=Auth(self.user), permissions=permissions.READ)

        component9 = ProjectFactory(creator=self.user, title='Nine')
        component9.add_contributor(userB, auth=Auth(self.user), permissions=permissions.READ)

        project1.add_pointer(component2, Auth(self.user))
        NodeRelation.objects.create(parent=project1, child=component4)
        NodeRelation.objects.create(parent=project1, child=component7)
        NodeRelation.objects.create(parent=component2, child=component3)
        NodeRelation.objects.create(parent=component4, child=component5)
        NodeRelation.objects.create(parent=component5, child=component6)
        NodeRelation.objects.create(parent=component7, child=component8)
        NodeRelation.objects.create(parent=component7, child=component9)

        nodes, all_readable = _get_readable_descendants(auth=Auth(userA), node=project1)
        assert (len(nodes)) == (3)
        assert not (all_readable)

        for node in nodes:
            assert (node.title) in (['Two', 'Six', 'Seven'])

        nodes, all_readable = _get_readable_descendants(auth=Auth(userB), node=project1)
        assert (len(nodes)) == (3)
        assert not (all_readable)
        for node in nodes:
            assert (node.title) in (['Four', 'Eight', 'Nine'])


class TestNodeLogSerializers(OsfTestCase):

    def test_serialize_node_for_logs(self):
        node = NodeFactory()
        d = node.serialize()

        assert (d['id']) == (node._primary_key)
        assert (d['category']) == (node.category_display)
        assert (d['node_type']) == (node.project_or_component)
        assert (d['url']) == (node.url)
        assert (d['title']) == (node.title)
        assert (d['api_url']) == (node.api_url)
        assert (d['is_public']) == (node.is_public)
        assert (d['is_registration']) == (node.is_registration)

    def test_get_mapcore_groups(self):
        from types import SimpleNamespace
        from api.logs.serializers import NodeLogParamsSerializer

        # Create two MapCoreGroup records
        g1 = MapCoreGroup.objects.create(_id='group-one')
        g2 = MapCoreGroup.objects.create(_id='group-two')

        # Params includes integers (PKs) and some non-integer noise
        params = {'mapcore_groups': [g1.id, 'invalid', g2.id, None]}

        # Non-anonymized request must include a user attribute
        req = SimpleNamespace(query_params={}, user=UserFactory())
        data = NodeLogParamsSerializer(params, context={'request': req}).data

        # Serializer should return only the created group objects ordered by _id
        assert ('mapcore_groups') in (data)
        assert (data['mapcore_groups']) == ([
                {'id': g1.id, 'name': g1._id},
                {'id': g2.id, 'name': g2._id},
            ])

        # Anonymized request should hide mapcore groups
        req_anon = SimpleNamespace(query_params={}, _is_anonymized=True, user=UserFactory())
        data_anon = NodeLogParamsSerializer(params, context={'request': req_anon}).data
        assert (data_anon.get('mapcore_groups', None)) == ([])

class TestAddContributorJson(OsfTestCase):

    def setUp(self):
        super(TestAddContributorJson, self).setUp()
        self.user = UserFactory()
        self.profile = self.user.profile_url
        self.user_id = self.user._primary_key
        self.fullname = self.user.fullname
        self.username = self.user.username

        self.jobs = [{
            'institution': 'School of Lover Boys',
            'department': 'Fancy Patter',
            'title': 'Lover Boy',
            'start': None,
            'end': None,
        }]

        self.schools = [{
            'degree': 'Vibing',
            'institution': 'Queens University',
            'department': '',
            'location': '',
            'start': None,
            'end': None,
        }]

    def test_add_contributor_json(self):
        # User with no employment or education info listed
        user_info = utils.add_contributor_json(self.user)

        assert (user_info['fullname']) == (self.fullname)
        assert (user_info['email']) == (self.username)
        assert (user_info['id']) == (self.user_id)
        assert (user_info['employment']) == (None)
        assert (user_info['education']) == (None)
        assert (user_info['n_projects_in_common']) == (0)
        assert (user_info['registered']) == (True)
        assert (user_info['active']) == (True)
        assert ('secure.gravatar.com') in (user_info['profile_image_url'])
        assert (user_info['profile_url']) == (self.profile)

    def test_add_contributor_json_with_edu(self):
        # Test user with only education information
        self.user.schools = self.schools
        user_info = utils.add_contributor_json(self.user)

        assert (user_info['fullname']) == (self.fullname)
        assert (user_info['email']) == (self.username)
        assert (user_info['id']) == (self.user_id)
        assert (user_info['employment']) == (None)
        assert (user_info['education']) == (self.user.schools[0]['institution'])
        assert (user_info['n_projects_in_common']) == (0)
        assert (user_info['registered']) == (True)
        assert (user_info['active']) == (True)
        assert ('secure.gravatar.com') in (user_info['profile_image_url'])
        assert (user_info['profile_url']) == (self.profile)

    def test_add_contributor_json_with_job(self):
        # Test user with only employment information
        self.user.jobs = self.jobs
        user_info = utils.add_contributor_json(self.user)

        assert (user_info['fullname']) == (self.fullname)
        assert (user_info['email']) == (self.username)
        assert (user_info['id']) == (self.user_id)
        assert (user_info['employment']) == (self.user.jobs[0]['institution'])
        assert (user_info['education']) == (None)
        assert (user_info['n_projects_in_common']) == (0)
        assert (user_info['registered']) == (True)
        assert (user_info['active']) == (True)
        assert ('secure.gravatar.com') in (user_info['profile_image_url'])
        assert (user_info['profile_url']) == (self.profile)

    def test_add_contributor_json_with_job_and_edu(self):
        # User with both employment and education information
        self.user.jobs = self.jobs
        self.user.schools = self.schools
        user_info = utils.add_contributor_json(self.user)

        assert (user_info['fullname']) == (self.fullname)
        assert (user_info['email']) == (self.username)
        assert (user_info['id']) == (self.user_id)
        assert (user_info['employment']) == (self.user.jobs[0]['institution'])
        assert (user_info['education']) == (self.user.schools[0]['institution'])
        assert (user_info['n_projects_in_common']) == (0)
        assert (user_info['registered']) == (True)
        assert (user_info['active']) == (True)
        assert ('secure.gravatar.com') in (user_info['profile_image_url'])
        assert (user_info['profile_url']) == (self.profile)


class TestSerializeMapcoreGroups(OsfTestCase):

    def test_serialize_mapcore_node_groups(self):
        user = UserFactory()
        node = NodeFactory(is_public=False)

        # two MapCore groups, one attached, one deleted
        g1 = MapCoreGroup.objects.create(_id='group-one')
        g2 = MapCoreGroup.objects.create(_id='group-two')

        auth1 = AuthGroup.objects.get_or_create(name=f'node_{node._id}_admin')[0]
        auth2 = AuthGroup.objects.get_or_create(name=f'node_{node._id}_read')[0]

        m1 = MapCoreNodeGroup.objects.create(node=node, group=auth1, mapcore_group=g1, creator=user, is_deleted=False)
        _m2 = MapCoreNodeGroup.objects.create(node=node, group=auth2, mapcore_group=g2, creator=user, is_deleted=True)

        data = utils.serialize_mapcore_node_groups(node)

        # only the non-deleted mapping should appear
        assert (len(data)) == (1)
        item = data[0]
        assert (item['id']) == (str(m1.id))
        assert (item['mapcore_group']['id']) == (g1.id)
        assert (item['mapcore_group']['name']) == (g1._id)
        assert (item['creator']) == (user.fullname)
        assert (item['is_deleted']) == (False)
        assert (item['permission']) == (m1.get_permission)
        assert (g1._id) in (item['url'])

    def test_serialize_parent_admin_groups(self):
        user = UserFactory()
        root = ProjectFactory()
        child = NodeFactory(parent=root)

        # admin group on root that should be exposed
        g_admin = MapCoreGroup.objects.create(_id='parent-admin')
        auth_admin = AuthGroup.objects.get_or_create(name=f'node_{root._id}_admin')[0]
        m_admin = MapCoreNodeGroup.objects.create(node=root, group=auth_admin, mapcore_group=g_admin, creator=user, is_deleted=False)

        # admin group on root that should be excluded via current_group
        g_excl = MapCoreGroup.objects.create(_id='parent-excl')
        auth_excl = AuthGroup.objects.get_or_create(name=f'node_{root._id}_admin')[0]
        m_excl = MapCoreNodeGroup.objects.create(node=root, group=auth_excl, mapcore_group=g_excl, creator=user, is_deleted=False)

        # Exclude g_excl by passing its id in current_group
        current_group = [g_excl.id]

        result = utils.serialize_parent_admin_groups(child, current_group)

        # Only the non-excluded admin mapping should be returned and permission should be 'read' per serializer
        assert (len(result)) == (1)
        r = result[0]
        assert (r['mapcore_group']['id']) == (g_admin.id)
        assert (r['mapcore_group']['name']) == (g_admin._id)
        assert (r['permission']) == ('read')
        assert (g_admin._id) in (r['url'])

    def test_serialize_parent_admin_groups_no_parent(self):
        user = UserFactory()
        node = NodeFactory()  # node with no parent

        # No current_group filters
        result = utils.serialize_parent_admin_groups(node, [])

        # Expect empty list when node has no parents
        assert (result) == ([])

    def test_serialize_mapcore_group_for_summary(self):
        user = UserFactory()
        node = NodeFactory(is_public=True)

        # two MapCore groups, one attached, one deleted
        g1 = MapCoreGroup.objects.create(_id='group-one')
        g2 = MapCoreGroup.objects.create(_id='group-two')

        auth1 = AuthGroup.objects.get_or_create(name=f'node_{node._id}_admin')[0]
        auth2 = AuthGroup.objects.get_or_create(name=f'node_{node._id}_read')[0]

        m1 = MapCoreNodeGroup.objects.create(node=node, group=auth1, mapcore_group=g1, creator=user, is_deleted=False, visible=True)
        _m2 = MapCoreNodeGroup.objects.create(node=node, group=auth2, mapcore_group=g2, creator=user, is_deleted=True, visible=True)

        data = serialize_mapcore_group_for_summary(node)

        # only the non-deleted mapping should appear
        assert ('mapcore_groups') in (data)
        assert (len(data['mapcore_groups'])) == (1)
        item = data['mapcore_groups'][0]
        assert (item['name']) == (g1._id)
        assert (g1._id) in (item['url'])

    def test_serialize_node_summary_includes_mapcore_groups(self):
        node = NodeFactory(is_public=True)
        user = node.creator

        # attach a MapCore group to the node
        g = MapCoreGroup.objects.create(_id='group-summary')
        auth_group = AuthGroup.objects.get_or_create(name=f'node_{node._id}_admin')[0]
        MapCoreNodeGroup.objects.create(node=node, group=auth_group, mapcore_group=g, creator=user, is_deleted=False, visible=True)

        summary = serialize_node_summary(node, Auth(user))
        assert ('mapcore_groups') in (summary)
        assert (len(summary['mapcore_groups'])) == (1)
        assert (summary['mapcore_groups'][0]['name']) == (g._id)
