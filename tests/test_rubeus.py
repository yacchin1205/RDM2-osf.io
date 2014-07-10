# -*- coding: utf-8 -*-
import os
import mock
from nose.tools import *
from webtest_plus import TestApp

from tests.base import OsfTestCase
from tests.factories import (UserFactory, ProjectFactory, NodeFactory,
    AuthFactory, PointerFactory, DashboardFactory)

from framework.auth import Auth
from website.util import rubeus

import website.app
app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)

class TestRubeus(OsfTestCase):

    def setUp(self):

        super(TestRubeus, self).setUp()

        self.project = ProjectFactory.build()
        self.consolidated_auth = Auth(user=self.project.creator)
        self.non_authenticator = UserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=self.consolidated_auth,
        )
        self.project.save()

        self.project.add_addon('s3', self.consolidated_auth)
        self.project.creator.add_addon('s3', self.consolidated_auth)
        self.node_settings = self.project.get_addon('s3')
        self.user_settings = self.project.creator.get_addon('s3')
        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.node_settings.bucket = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.user_settings
        self.node_settings.save()

    def test_hgrid_dummy(self):
        node_settings = self.node_settings
        node = self.project
        user = Auth(self.project.creator)
        # FIXME: These tests are very brittle.
        rv = {
            'isPointer': False,
            'addon': 's3',
            'addonFullname': node_settings.config.full_name,
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon Simple Storage Service: {0}'.format(
                node_settings.bucket
            ),
            'kind': 'folder',
            'permissions': {
                'view': node.can_view(user),
                'edit': node.can_edit(user) and not node.is_registration,
            },
            'urls': {
                'fetch': node.api_url + 's3/hgrid/',
                'upload': node.api_url + 's3/'
            },
            'accept': {
                'maxSize': node_settings.config.max_file_size,
                'acceptedFiles': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
            'extra': None,
            'buttons': None,
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        assert_equals(
            rubeus.build_addon_root(
                node_settings, node_settings.bucket, permissions=permissions
            ),
            rv
        )

    def test_hgrid_dummy_fail(self):
        node_settings = self.node_settings
        node = self.project
        user = Auth(self.project.creator)
        rv = {
            'isPointer': False,
            'addon': 's3',
            'addonFullname': node_settings.config.full_name,
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon Simple Storage Service: {0}'.format(
                node_settings.bucket
            ),
            'kind': 'folder',
            'permissions': {
                'view': node.can_view(user),
                'edit': node.can_edit(user) and not node.is_registration,
            },
            'urls': {
                'fetch': node.api_url + 's3/hgrid/',
                'upload': node.api_url + 's3/upload/'
            },
            'accept': {
                'maxSize': node_settings.config.max_file_size,
                'acceptedFiles': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        assert_not_equals(rubeus.build_addon_root(
            node_settings, node_settings.bucket, permissions=permissions), rv)

    def test_hgrid_dummy_overrides(self):
        node_settings = self.node_settings
        node_settings.config.urls = None
        node = self.project
        user = Auth(self.project.creator)
        rv = {
            'isPointer': False,
            'addon': 's3',
            'addonFullname': node_settings.config.full_name,
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon Simple Storage Service: {0}'.format(
                node_settings.bucket
            ),
            'kind': 'folder',
            'permissions': {
                'view': node.can_view(user),
                'edit': node.can_edit(user) and not node.is_registration,
            },
            'urls': {},
            'accept': {
                'maxSize': node_settings.config.max_file_size,
                'acceptedFiles': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
            'extra': None,
            'buttons': None,
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        assert_equals(
            rubeus.build_addon_root(
                node_settings, node_settings.bucket,
                permissions=permissions, urls={}
            ),
            rv
        )

    def test_hgrid_dummy_node_urls(self):
        node_settings = self.node_settings
        user = Auth(self.project.creator)

        node = self.project
        node_settings.config.urls = {
            'fetch': node.api_url + 's3/hgrid/',
            'upload': node.api_url + 's3/upload/'
        }

        rv = {
            'isPointer': False,
            'addon': 's3',
            'addonFullname': node_settings.config.full_name,
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon Simple Storage Service: {0}'.format(
                node_settings.bucket
            ),
            'kind': 'folder',
            'permissions': {
                'view': node.can_view(user),
                'edit': node.can_edit(user) and not node.is_registration,
            },
            'urls': {
                'fetch': node.api_url + 's3/hgrid/',
                'upload': node.api_url + 's3/upload/'
            },
            'accept': {
                'maxSize': node_settings.config.max_file_size,
                'acceptedFiles': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
            'extra': None,
            'buttons': None,
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        assert_equals(
            rubeus.build_addon_root(
                node_settings, node_settings.bucket, permissions=permissions
            ),
            rv
        )

    def test_serialize_private_node(self):
        user = UserFactory()
        auth = Auth(user=user)
        public = ProjectFactory.build(is_public=True)
        public.add_contributor(user)
        public.save()
        private = ProjectFactory(project=public, is_public=False)
        NodeFactory(project=private)
        collector = rubeus.NodeFileCollector(node=public, auth=auth)

        private_dummy = collector._serialize_node(private)
        assert_false(private_dummy['permissions']['edit'])
        assert_false(private_dummy['permissions']['view'])
        assert_equal(private_dummy['name'], 'Private Component')
        assert_equal(len(private_dummy['children']), 0)

    def test_collect_components_deleted(self):
        node = NodeFactory(creator=self.project.creator, project=self.project)
        node.is_deleted = True
        collector = rubeus.NodeFileCollector(
            self.project, Auth(user=UserFactory())
        )
        nodes = collector._collect_components(self.project, visited=[])
        assert_equal(len(nodes), 0)

    def test_serialized_pointer_has_flag_indicating_its_a_pointer(self):
        pointer = PointerFactory()
        serializer = rubeus.NodeFileCollector(node=pointer, auth=self.consolidated_auth)
        ret = serializer._serialize_node(pointer)
        assert_true(ret['isPointer'])

class TestSerializingDashboard(OsfTestCase):

    def setUp(self):
        pass

    smart_folder_types = {
        'name': str,
        'children': list,
        'node_id': str
    }
    smart_folder_values = {
        'kind': 'folder',
        'contributors': [],
        'parentIsFolder': True,
        'isPointer': False,
        'isFolder': True,
        'dateModified': None,
        'modifiedDelta': 0,
        'modifiedBy': None,
        'isSmartFolder': True,
        'urls': {
            'upload': None,
            'fetch': None
        },
        'isDashboard': False,
        'expand': False,
        'permissions': {
            'edit': False,
            'acceptsDrops': False,
            'copyable': False,
            'movable': False,
            'view': True
        }
    }
    amp_str = 'All my projects'
    amr_str = 'All my registrations'
    def test_serialize_empty_dashboard(self):
        dash = DashboardFactory()
        auth = AuthFactory(user=dash.creator)

        amp_str = self.amp_str
        amr_str = self.amr_str

        rv = rubeus.to_project_hgrid(dash, auth)

        # there are only 2 folders
        assert_equal(len(rv), 2)
        # and the 2 smart folders are named thusly
        assert_equal({amp_str, amr_str}, {v['name'] for v in rv})

        # TODO rewrite this in a more readable way
        amp, amr = None, None
        for v in rv:
            if v['name'] == amp_str:
                amp = v
            elif v['name'] == amr_str:
                amr = v
            else:
                # TODO Represent this better :/
                assert_true(False)

        assert_equal(amp['node_id'], '-amp')
        assert_equal(amr['node_id'], '-amr')

        for v in rv:
            assert_equal(v['children'], [])
            for attr, correct_value in self.smart_folder_values.items():
                # TODO this will fail if something is added to one of the dictionaries in rv, e.g. rv['permissions']
                # Is that ok?
                assert_equal(correct_value, v[attr])
            for attr, correct_type in self.smart_folder_types.items():
                assert_equal(correct_type, type(v[attr]))



        # for v in rv:





        # pass to rubeus.to_project_hgrid

    # def test_serialize_folder_containing_folder(self):
    #     pass
    #
    # def test_serialize_folder_containing_project(self):
    #     pass




# TODO: Make this more reusable across test modules
mock_addon = mock.Mock()
serialized = {
    'addon': 'mockaddon',
    'name': 'Mock Addon',
    'isAddonRoot': True,
    'extra': '',
    'permissions': {'view': True, 'edit': True},
    'urls': {
        'fetch': '/fetch',
        'delete': '/delete'
    }
}
mock_addon.config.get_hgrid_data.return_value = [serialized]

class TestSerializingNodeWithAddon(OsfTestCase):
    def setUp(self):
        self.auth = AuthFactory()
        self.project = ProjectFactory(creator=self.auth.user)
        self.project.get_addons = mock.Mock()
        self.project.get_addons.return_value = [mock_addon]
        self.serializer = rubeus.NodeFileCollector(node=self.project, auth=self.auth)

    def test_collect_addons(self):
        ret = self.serializer._collect_addons(self.project)
        assert_equal(ret, [serialized])

    def test_serialize_node(self):
        ret = self.serializer._serialize_node(self.project)
        assert_equal(
            len(ret['children']),
            len(self.project.get_addons.return_value) + len(self.project.nodes)
        )
        assert_equal(ret['kind'], rubeus.FOLDER)
        assert_equal(ret['name'], 'Project: {0}'.format(self.project.title))
        assert_equal(ret['permissions'], {
            'view': True,
            'edit': True
        })
        assert_equal(
            ret['urls'],
            {
                'upload': os.path.join(self.project.api_url, 'osffiles') + '/',
                'fetch': None
            },
            'project root data has no upload or fetch urls'
        )

    def test_collect_js_recursive(self):
        self.project.get_addons.return_value[0].config.include_js = {'files': ['foo.js']}
        node = NodeFactory(project=self.project)
        mock_node_addon = mock.Mock()
        mock_node_addon.config.include_js = {'files': ['bar.js', 'baz.js']}
        node.get_addons = mock.Mock()
        node.get_addons.return_value = [mock_node_addon]
        assert_equal(
            rubeus.collect_addon_js(self.project),
            {'foo.js', 'bar.js', 'baz.js'}
        )

    def test_collect_js_unique(self):
        self.project.get_addons.return_value[0].config.include_js = {'files': ['foo.js']}
        node = NodeFactory(project=self.project)
        mock_node_addon = mock.Mock()
        mock_node_addon.config.include_js = {'files': ['foo.js', 'baz.js']}
        node.get_addons = mock.Mock()
        node.get_addons.return_value = [mock_node_addon]
        assert_equal(
            rubeus.collect_addon_js(self.project),
            {'foo.js', 'baz.js'}
        )


