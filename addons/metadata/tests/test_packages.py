# -*- coding: utf-8 -*-
"""Export and import tests of the metadata addon."""
import io
import json
import logging
import os
import shutil
import tempfile
from zipfile import ZipFile

import mock
from nose.tools import *  # noqa (PEP8 asserts)
import pytest
from tests.base import OsfTestCase

from framework.auth import Auth
from osf.models.metaschema import RegistrationSchema
from osf_tests.factories import ProjectFactory, CommentFactory
from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory

from ..packages import ROCrateFactory, ROCrateExtractor


logger = logging.getLogger(__name__)


def _create_waterbutler_object(provider, file):
    def _download_to(f):
        f.write(file['content'])

    def _get_files():
        assert file['kind'] == 'folder'
        return [
            _create_waterbutler_object(provider, file)
            for file in file['children']
        ]

    obj = mock.MagicMock()
    obj.attributes = file
    obj.provider = provider
    obj.kind = file['kind']
    obj.name = file['name']
    obj.path = file['path']
    obj.materialized = file['materialized']
    if file['kind'] == 'file':
        obj.contentType = file.get('contentType', None)
        obj.size = len(file['content'])
        obj.modified_utc= None
        obj.created_utc= None

    obj.download_to = mock.MagicMock(side_effect=_download_to)
    obj.get_files = mock.MagicMock(side_effect=_get_files)
    return obj

def _create_waterbutler_client(new_node, files):
    def _get_root_files(name):
        logger.info(f'_get_root_files: {name}')
        if name not in files:
            return []
        return [
            _create_waterbutler_object(name, file)
            for file in files[name]
        ]
    mock_upload_file = mock.MagicMock()
    def _get_file_by_materialized_path(path, create=False):
        def _upload_file(data_path, dest_name):
            buf = io.BytesIO()
            with open(data_path, 'rb') as f:
                shutil.copyfileobj(f, buf)
            mock_upload_file(path, dest_name, buf.getvalue())
            r = mock.MagicMock()
            provider = path.split('/')[0]
            root_file = new_node.get_addon(provider).get_root().append_file(dest_name)
            r.provider = provider
            r.path = root_file.path
            return r
        obj = mock.MagicMock()
        obj.upload_file = mock.MagicMock(side_effect=_upload_file)
        return obj
    wb = mock.MagicMock()
    wb.get_root_files = mock.MagicMock(side_effect=_get_root_files)
    wb.get_file_by_materialized_path = mock.MagicMock(side_effect=_get_file_by_materialized_path)
    return wb, mock_upload_file

def _get_ro_crate_from(zip_path):
    with ZipFile(zip_path, 'r') as zf:
        return json.load(zf.open('ro-crate-metadata.json'))

class TestExportAndImport(OsfTestCase):

    def setUp(self):
        super(TestExportAndImport, self).setUp()
        self.work_dir = tempfile.mkdtemp()
        self.node = ProjectFactory()
        self.node.add_addon('metadata', auth=Auth(self.node.creator))
        self.node.description = 'TEST_DESCRIPTION'
        self.node.add_tags(['Test Node'], auth=Auth(user=self.node.creator), log=False)
        self.node.save()
        self.node_comment_1 = CommentFactory(node=self.node, user=self.node.creator)
        self.node_comment_1.content = 'Comment for the node'
        self.node_comment_1.save()
        root_file = self.node.get_addon('osfstorage').get_root().append_file('file_in_root')
        root_file_comment = CommentFactory(
            node=self.node,
            user=self.node.creator,
            target=root_file.get_guid(create=True),
        )
        root_file_comment.content = 'Comment for the file file_in_root'
        root_file_comment.save()
        file = self.node.get_addon('osfstorage').get_root().append_file('file_in_folder')
        file.add_tags(['Test File'], auth=Auth(user=self.node.creator), log=False)
        file.save()
        sub_file = self.node.get_addon('osfstorage').get_root().append_file('file_in_sub_folder')

        self.wb, _ = _create_waterbutler_client(self.node, {
            'osfstorage': [
                {
                    'provider': 'osfstorage',
                    'kind': 'folder',
                    'name': 'sample',
                    'path': '/SAMPLE/',
                    'materialized': '/sample/',
                    'children': [
                        {
                            'provider': 'osfstorage',
                            'kind': 'file',
                            'name': 'file_in_folder',
                            'path': file.path,
                            'materialized': '/sample/file_in_folder',
                            'content': b'FOLDER_DATA',
                        },
                        {
                            'provider': 'osfstorage',
                            'kind': 'folder',
                            'name': 'sub_folder',
                            'path': '/SUB_FOLDER/',
                            'materialized': '/sample/sub_folder/',
                            'children': [
                                {
                                    'provider': 'osfstorage',
                                    'kind': 'file',
                                    'name': 'file_in_sub_folder',
                                    'path': sub_file.path,
                                    'materialized': '/sample/sub_folder/file_in_sub_folder',
                                    'content': b'SUB_FOLDER_DATA',
                                }
                            ],
                        },
                        {
                            'provider': 'osfstorage',
                            'kind': 'folder',
                            'name': 'empty',
                            'path': '/EMPTY/',
                            'materialized': '/sample/empty/',
                            'children': [],
                        }
                    ],
                },
                {
                    'provider': 'osfstorage',
                    'kind': 'file',
                    'name': 'file_in_root',
                    'path': root_file.path,
                    'materialized': '/file_in_root',
                    'content': b'ROOT_DATA',
                },
            ]
        })
        schema = RegistrationSchema.objects.get(name='公的資金による研究データのメタデータ登録')
        self.node.get_addon('metadata').set_file_metadata('osfstorage/file_in_root', {
            'path': 'osfstorage/file_in_root',
            'folder': False,
            'hash': '1234567890',
            'items': [
                {
                    'active': True,
                    'schema': schema._id,
                    'data': {
                        'test': True,
                    },
                },
            ],
        }, auth=Auth(self.node.creator))
        self.node.get_addon('metadata').set_file_metadata('osfstorage/sample/sub_folder/', {
            'path': 'osfstorage/sample/sub_folder/',
            'folder': True,
            'hash': '1234567890',
            'items': [
                {
                    'active': True,
                    'schema': schema._id,
                    'data': {
                        'test': True,
                        'this_is_folder': True,
                    },
                },
            ],
        }, auth=Auth(self.node.creator))
        wiki_page = WikiFactory(node=self.node, page_name='test')
        wiki = WikiVersionFactory(wiki_page=wiki_page)
        wiki.content = 'Test Wiki Page'
        wiki.save()

    def tearDown(self):
        shutil.rmtree(self.work_dir)
        super(TestExportAndImport, self).tearDown()

    def test_config_disable(self):
        config = {
            'comment': {
                'enable': False,
            },
            'log': {
                'enable': False,
            },
        }
        rocrate = ROCrateFactory(self.node, self.work_dir, self.wb, config)
        zip_path = os.path.join(self.work_dir, 'package.zip')
        rocrate.download_to(zip_path)

        json_entities = _get_ro_crate_from(zip_path)
        assert_equals(len([e for e in json_entities['@graph'] if e['@type'] == 'Comment']), 0)
        assert_equals(len([e for e in json_entities['@graph'] if e['@type'] == 'Action']), 0)

    def test_simple(self):
        config = {
            'addons': {
                'osfstorage': {},
            }
        }
        rocrate = ROCrateFactory(self.node, self.work_dir, self.wb, config)
        zip_path = os.path.join(self.work_dir, 'package.zip')
        rocrate.download_to(zip_path)

        json_entities = _get_ro_crate_from(zip_path)
        logger.info(f'ro-crate: {json.dumps(json_entities, indent=2)}')
        assert_equals(len([e for e in json_entities['@graph'] if e['@type'] == 'Comment']), 2)
        assert_equals(
            [e['name'] for e in json_entities['@graph'] if e['@type'] == 'Action'],
            ['metadata_file_added', 'metadata_file_added', 'addon_added', 'project_created'],
        )

        zip_buf = io.BytesIO()
        with open(zip_path, 'rb') as f:
            shutil.copyfileobj(f, zip_buf)

        with mock.patch.object(ROCrateExtractor, '_download') as mock_request:
            def to_file(f):
                zip_buf.seek(0)
                shutil.copyfileobj(zip_buf, f)
            mock_request.side_effect = to_file

            new_node = ProjectFactory()
            new_node.add_addon('metadata', auth=Auth(user=new_node.creator))
            extractor = ROCrateExtractor(
                new_node.creator,
                'http://test.rdm.nii.ac.jp/test-data.zip',
                self.work_dir,
            )
            new_wb, new_wb_upload_file = _create_waterbutler_client(new_node, {})
            extractor.ensure_node(new_node)
            extractor.ensure_folders(new_node, new_wb, './osfstorage/')
            for file_extractor in extractor.file_extractors:
                file_extractor.extract(new_node, new_wb)

            assert_equals(new_node.description, 'TEST_DESCRIPTION')
            assert_equals([t.name for t in new_node.tags.all()], ['Test Node'])

            assert_equals(
                [
                    t.name
                    for t in new_node.get_addon('osfstorage').get_root().find_child_by_name('file_in_folder').tags.all()
                ],
                ['Test File'],
            )
            schema = RegistrationSchema.objects.get(name='公的資金による研究データのメタデータ登録')
            assert_equals(
                new_node.get_addon('metadata').get_file_metadata_for_path('osfstorage/file_in_root')['items'],
                [
                    {
                        'active': True,
                        'schema': schema._id,
                        'data': {
                            'test': True,
                        },
                    },
                ],
            )
            assert_equals(
                new_node.get_addon('metadata').get_file_metadata_for_path('osfstorage/sample/sub_folder/')['items'],
                [
                    {
                        'active': True,
                        'schema': schema._id,
                        'data': {
                            'test': True,
                            'this_is_folder': True,
                        },
                    },
                ],
            )
            new_wb.assert_has_calls([
                mock.call.get_file_by_materialized_path('osfstorage/sample/', create=True),
                mock.call.get_file_by_materialized_path('osfstorage/sample/sub_folder/', create=True),
                mock.call.get_file_by_materialized_path('osfstorage/sample/empty/', create=True),
                mock.call.get_file_by_materialized_path('osfstorage/sample/'),
                mock.call.get_file_by_materialized_path('osfstorage/sample/sub_folder/'),
                mock.call.get_file_by_materialized_path('osfstorage/'),
            ])
            new_wb_upload_file.assert_has_calls([
                mock.call('osfstorage/sample/', 'file_in_folder', b'FOLDER_DATA'),
                mock.call('osfstorage/sample/sub_folder/', 'file_in_sub_folder', b'SUB_FOLDER_DATA'),
                mock.call('osfstorage/', 'file_in_root', b'ROOT_DATA'),
            ])
            assert_equals(
                new_node.wikis.get(page_name='test').get_version().content,
                'Test Wiki Page',
            )
