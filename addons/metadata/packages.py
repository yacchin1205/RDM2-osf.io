from datetime import datetime
import io
import json
import logging
import os
import re
import shutil
import tempfile
from zipfile import ZipFile

import furl
from django.contrib.contenttypes.models import ContentType
from rocrate.rocrate import ROCrate
from rocrate.model.person import Person
from rocrate.model.contextentity import ContextEntity
from rocrate.model.data_entity import DataEntity
from rest_framework import status as http_status
import requests
import zipfly

from api.nodes.serializers import NodeSerializer
from api.base.utils import waterbutler_api_url_for
from framework.auth import Auth
from framework.celery_tasks import app as celery_app
from framework.exceptions import HTTPError
from osf.models import Guid, OSFUser, AbstractNode, Comment, BaseFileNode
from website.util import waterbutler
from website import settings as website_settings
from osf.models.metaschema import RegistrationSchema
from . import SHORT_NAME
from .jsonld import (
    convert_metadata_to_json_ld_entities,
    convert_json_ld_entity_to_metadata_item,
)
from addons.wiki.models import WikiPage
from addons.weko import settings as weko_settings


logger = logging.getLogger(__name__)


DEFAULT_ADDONS_FILES = [{
    'materialized': '/.weko/',
    'enable': False,
}]


class RequestWrapper(object):
    def __init__(self, auth):
        self.auth = auth

    @property
    def user(self):
        logger.info(f'USER: {self.auth.user}')
        return self.auth.user

    @property
    def method(self):
        return 'PUT'

    @property
    def GET(self):
        return {}

class WaterButlerClient(object):
    def __init__(self, user, node):
        self.cookie = user.get_or_create_cookie().decode()
        self.node = node

    def get_root_files(self, name):
        response = requests.get(
            waterbutler_api_url_for(
                self.node._id, name, path='/', _internal=True, meta=''
            ),
            headers={'content-type': 'application/json'},
            cookies={website_settings.COOKIE_NAME: self.cookie}
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()['data']
        return [WaterButlerObject(file, self) for file in data]

    def create_root_folder(self, provider, folder_name):
        resp = waterbutler.create_folder(
            self.cookie, self.node._id, folder_name, f'{provider}/',
        )
        data = resp.json()
        return WaterButlerObject(data, self)

    def resolve_file_path(self, dest_path):
        f = self._get_file(dest_path)
        if f is None:
            raise IOError(f'File not found: {dest_path}')
        logger.debug(f'Resolved: {dest_path} = {f}')
        if 'attributes' not in f:
            raise ValueError('No attributes')
        return dest_path.split('/')[0] + f['attributes']['path']

    def upload_root_file(self, file, file_name, provider):
        resp = waterbutler.upload_file(self.cookie, self.node._id, file, file_name, provider)
        data = resp.json()['data']
        return WaterButlerObject(data, self)

    def get_file_by_materialized_path(self, path, create=False):
        logger.debug(f'Search: {path}')
        path_segments = path.split('/')
        folder = path_segments[-1] == ''
        if folder:
            path_segments = path_segments[:-1]
        if len(path_segments) == 0:
            raise IOError('Empty path')
        if len(path_segments) == 1:
            return WaterButlerProvider(path_segments[0], self)
        if len(path_segments) == 2:
            provider = path_segments[0]
            target_path = '/'.join(path_segments[1:])
            if folder:
                target_path += '/'
            logger.debug(f'Fetching... provider={provider}, path={target_path}')
            files = self.get_root_files(provider)
            logger.debug(f'Fetched: provider={provider}, path={target_path}, files={files}')
            candidates = [
                file
                for file in files
                if 'materialized' in file.attributes and file.attributes['materialized'] == f'/{target_path}'
            ]
            if create and len(candidates) == 0:
                return self.create_root_folder(provider, path_segments[1])
            return candidates[0] if len(candidates) else None
        parent_path = '/'.join(path_segments[:-1]) + '/'
        parent_file = self.get_file_by_materialized_path(parent_path, create=create)
        target_path = '/'.join(path_segments[1:])
        if folder:
            target_path += '/'
        logger.debug(f'Fetching... path={target_path}')
        files = parent_file.get_files()
        logger.debug(f'Fetched: path={target_path}, files={files}')
        candidates = [
            file
            for file in files
            if 'materialized' in file.attributes and file.attributes['materialized'] == f'/{target_path}'
        ]
        if create and len(candidates) == 0:
            return parent_file.create_folder(path_segments[-1])
        return candidates[0] if len(candidates) else None

class WaterButlerProvider(object):
    def __init__(self, provider, wb):
        self.provider = provider
        self.wb = wb
        self._children = {}

    def get_files(self):
        return self.wb.get_root_files(self.provider)

    def create_folder(self, folder_name):
        return self.wb.create_root_folder(self.provider, folder_name)

    def upload_file(self, file, file_name):
        return self.wb.upload_root_file(file, file_name, self.provider)

class WaterButlerObject(object):
    def __init__(self, resp, wb):
        self.raw = resp
        self.wb = wb
        self._children = {}

    def get_files(self):
        logger.debug(f'list files: {self.links}')
        url = furl.furl(website_settings.WATERBUTLER_INTERNAL_URL)
        file_url = furl.furl(self.links['new_folder'])
        url.path = str(file_url.path)
        response = requests.get(
            url.url,
            headers={'content-type': 'application/json'},
            cookies={website_settings.COOKIE_NAME: self.wb.cookie}
        )
        response.raise_for_status()
        return [WaterButlerObject(f, self.wb) for f in response.json()['data']]

    def download_to(self, f):
        logger.debug(f'download content: {self.links}')
        url = furl.furl(website_settings.WATERBUTLER_INTERNAL_URL)
        file_url = furl.furl(self.links['download'])
        url.path = str(file_url.path)
        response = requests.get(
            url.url,
            headers={'content-type': 'application/json'},
            cookies={website_settings.COOKIE_NAME: self.wb.cookie},
            stream=True,
        )
        response.raise_for_status()
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    def delete(self):
        url = furl.furl(website_settings.WATERBUTLER_INTERNAL_URL)
        file_url = furl.furl(self.links['delete'])
        url.path = str(file_url.path)
        response = requests.delete(
            url.url,
            headers={'content-type': 'application/json'},
            cookies={website_settings.COOKIE_NAME: self.wb.cookie},
        )
        response.raise_for_status()

    def create_folder(self, folder_name):
        provider = self.raw['attributes']['provider']
        path = self.raw['attributes']['path']
        resp = waterbutler.create_folder(
            self.wb.cookie, self.wb.node._id, folder_name,
            provider + path,
        )
        data = resp.json()
        return WaterButlerObject(data, self.wb)

    def upload_file(self, file, file_name):
        provider = self.raw['attributes']['provider']
        path = self.raw['attributes']['path']
        resp = waterbutler.upload_file(
            self.wb.cookie, self.wb.node._id, file, file_name,
            provider + path,
        )
        data = resp.json()['data']
        return WaterButlerObject(data, self.wb)

    @property
    def guid(self):
        return self.raw['id']

    @property
    def attributes(self):
        return self.raw['attributes']

    @property
    def links(self):
        return self.raw['links']

    def __getattr__(self, name):
        attr = self.raw['attributes']
        if name in attr:
            return attr[name]
        raise AttributeError(name)

class GeneratorIOStream(io.RawIOBase):

    def __init__(self, iter):
        self._iter = iter
        self._left = b''

    def _read1(self, size=None):
        while not self._left:
            try:
                self._left = next(self._iter)
            except StopIteration:
                break
        ret = self._left[:size]
        self._left = self._left[len(ret):]
        return ret

    def readall(self):
        r = []
        while True:
            m = self._read1()
            if not m:
                break
            r.append(m)
        return b''.join(r)

    def readinto(self, b):
        pos = 0
        while pos < len(b):
            n = len(b) - pos
            m = self._read1(n)
            if not m:
                break
            for i, v in enumerate(m):
                b[pos + i] = v
            pos += len(m)
        return pos

def _as_web_file(node, wb_file):
    if wb_file.provider == 'osfstorage':
        file_id = re.match(r'^/([^/]+)$', wb_file.path).group(1)
        logger.debug(f'web_file({wb_file.path}): {file_id}')
        return BaseFileNode.objects.filter(
            _id=file_id,
            provider=wb_file.provider,
            target_object_id=node.id,
            deleted=None,
            target_content_type_id=ContentType.objects.get_for_model(AbstractNode),
        ).first()
    return BaseFileNode.objects.filter(
        _path=wb_file.path,
        provider=wb_file.provider,
        target_object_id=node.id,
        deleted=None,
        target_content_type_id=ContentType.objects.get_for_model(AbstractNode),
    ).order_by('-id').first()

class BaseROCrateFactory(object):

    def __init__(self, node, work_dir):
        self.node = node
        self.work_dir = work_dir
        self.include_users = False

    def _ro_crate_path_list(self):
        crate = ROCrate()
        crate.metadata.extra_terms.update({
            'isReplacedBy': 'http://purl.org/dc/terms/isReplacedBy',
        })

        crate, files = self._build_ro_crate(crate)
        metadata_file = os.path.join(self.work_dir, 'ro-crate-metadata.json')
        zip_path = os.path.join(self.work_dir, 'work.zip')
        crate.write_zip(zip_path)
        with ZipFile(zip_path, 'r') as zf:
            with zf.open('ro-crate-metadata.json') as f:
                metadata = f.read()
                with open(metadata_file, 'wb') as df:
                    df.write(metadata)
        yield {
            'fs': metadata_file,
            'n': 'ro-crate-metadata.json',
        }
        tmp_path = os.path.join(self.work_dir, 'temp.dat')
        for path, file, _ in files:
            logger.info(f'Downloading... {path}')
            assert path.startswith('./'), path
            with open(tmp_path, 'wb') as df:
                file.download_to(df)
            yield {
                'fs': tmp_path,
                'n': path[2:],
            }

    def _get_jpcoar_context(self):
        return {
            'dc': 'http://purl.org/dc/terms/',
            'datacite': 'https://schema.datacite.org/meta/kernel-4/',
            'jpcoar': 'https://github.com/JPCOAR/schema/blob/master/1.0/',
        }

    def _build_ro_crate(self, crate):
        raise NotImplementedError()

    def download_to(self, zip_path):
        zfly = zipfly.ZipFly(paths=self._ro_crate_path_list())
        with open(zip_path, 'wb') as f:
            shutil.copyfileobj(GeneratorIOStream(zfly.generator()), f)
        logger.debug(f'Downloaded: {os.path.getsize(zip_path)}')

    def _is_file_archivable(self, wb_file):
        return True

    def _create_file_entities(self, crate, base_path, wb_file, user_ids):
        path = os.path.join(base_path, wb_file.name)
        if not self._is_file_archivable(wb_file):
            logger.info(f'File is not target: {path}')
            return []
        r = []
        if wb_file.attributes['kind'] == 'folder':
            path += '/'
            wb_files = wb_file.get_files()
            for child in wb_files:
                r += self._create_file_entities(crate, path, child, user_ids)
            crate.add(DataEntity(crate, path, properties={
                '@type': 'StorageProvider' if wb_file.path == '/' else 'Folder',
                'name': wb_file.name,
                'hasPart': [
                    {'@id': f'{path}{child.name}' if child.attributes['kind'] == 'folder' else f'{path[2:]}{child.name}'}
                    for child in wb_files
                ]
            }))
        else:
            web_file = _as_web_file(self.node, wb_file)
            comments = []
            tags = []
            creator = None
            if web_file is not None:
                latest = web_file.versions.order_by('-created').first()
                if latest is not None:
                    creator = latest.creator
                if self.include_users and creator._id not in user_ids:
                    self._create_contributor_entities(crate, creator, user_ids)
                comments = sum([
                    self._create_comment_entities(crate, path, c, user_ids)
                    for c in Comment.objects.filter(root_target=web_file.get_guid(), deleted__isnull=True)
                ], [])
                tags += [t.name for t in web_file.tags.all()]
            r.append((path, wb_file, comments))
            props = {
                'name': wb_file.name,
                'encodingFormat': wb_file.contentType,
                'contentSize': str(wb_file.size),
                'dateModified': wb_file.modified_utc,
                'dateCreated': wb_file.created_utc,
                'keywords': tags,
            }
            if creator is not None and creator._id in user_ids:
                props['creator'] = user_ids[creator._id]
            crate.add_file(path, dest_path=path, properties=props)
        self._create_file_metadata_entities(crate, path, self._get_materialized_path(wb_file))
        return r

    def _get_materialized_path(self, wb_file):
        if 'materialized' not in wb_file.attributes:
            raise ValueError('Materialized path not defined')
        return wb_file.attributes['provider'] + wb_file.attributes['materialized']

    def _create_file_metadata_entities(self, crate, path, file_path):
        metadata = self.node.get_addon(SHORT_NAME)
        if metadata is None:
            return
        file_metadata = metadata.get_file_metadata_for_path(file_path, resolve_parent=False)
        if file_metadata is None:
            return
        file_entity_id = path
        if not file_metadata['folder'] and file_entity_id.startswith('./'):
            file_entity_id = file_entity_id[2:]
        for i, entity in enumerate(convert_metadata_to_json_ld_entities(file_metadata)):
            props = {
                '@context': 'https://purl.org/rdm/file-metadata/0.1',
            }
            props.update(entity)
            props['about'] = {
                '@id': file_entity_id,
            }
            crate.add(ContextEntity(crate, f'{file_entity_id}#{i}', properties=props))

    def _create_comment_entities(self, crate, parent_id, comment, user_ids):
        if self.include_users and comment.user._id not in user_ids:
            self._create_contributor_entities(crate, comment.user, user_ids)
        comment_id = f'#comment#{comment._id}'
        r = [ContextEntity(crate, comment_id, properties={
            '@type': 'Comment',
            'dateCreated': _to_datetime(comment.created),
            'dateModified': _to_datetime(comment.modified),
            'parentItem': {
                '@id': parent_id,
            },
            'text': comment.content,
            'author': {
                '@id': user_ids[comment.user._id]
            } if comment.user._id in user_ids else None
        })]
        for reply in Comment.objects.filter(target___id=comment._id, deleted__isnull=True):
            r += self._create_comment_entities(crate, comment_id, reply, user_ids)
        return r

    def _create_creator_entities(self, crate, user, user_ids):
        if user._id not in user_ids:
            entity_id = f'#creator#{len(user_ids)}'
            user_ids[user._id] = entity_id
        else:
            entity_id = user_ids[user._id]
        return [
            Person(crate, entity_id, properties={
                'name': user.fullname,
                'affiliation': [e.name for e in user.affiliated_institutions.all()],
                'isReplacedBy': {
                    '@id': f'{entity_id}.jpcoar',
                }
            }),
            ContextEntity(crate, f'{entity_id}.jpcoar', properties={
                '@context': self._get_jpcoar_context(),
                '@type': 'Creator',
                'jpcoar:creatorName': _to_localized(user, 'fullname'),
                'jpcoar:givenName': _to_localized(user, 'given_name'),
                'jpcoar:familyName': _to_localized(user, 'family_name'),
                'jpcoar:affiliation': [{
                    '@type': 'Affiliation',
                    'jpcoar:affiliationName': _to_localized(e, 'name'),
                } for e in user.affiliated_institutions.all()],
            })
        ]

    def _create_contributor_entities(self, crate, user, user_ids):
        if user._id in user_ids:
            return []
        entity_id = f'#contributor#{len(user_ids)}'
        user_ids[user._id] = entity_id
        return [
            Person(crate, entity_id, properties={
                'name': user.fullname,
                'affiliation': [e.name for e in user.affiliated_institutions.all()],
                'isReplacedBy': {
                    '@id': f'{entity_id}.jpcoar',
                }
            }),
            ContextEntity(crate, f'{entity_id}.jpcoar', properties={
                '@context': self._get_jpcoar_context(),
                '@type': 'Contributor',
                'jpcoar:contributorName': _to_localized(user, 'fullname'),
                'jpcoar:givenName': _to_localized(user, 'given_name'),
                'jpcoar:familyName': _to_localized(user, 'family_name'),
                'jpcoar:affiliation': [{
                    '@type': 'Affiliation',
                    'jpcoar:affiliationName': _to_localized(e, 'name'),
                } for e in user.affiliated_institutions.all()],
            })
        ]

class WikiFile(object):
    def __init__(self, wiki):
        self.wiki = wiki

    def download_to(self, f):
        latest = self.wiki.get_version()
        if latest is None:
            logger.warn(f'Wiki content is empty: {self.wiki.page_name}')
            return
        f.write(latest.content.encode('utf8'))

class ROCrateFactory(BaseROCrateFactory):

    def __init__(self, node, work_dir, wb, config):
        super(ROCrateFactory, self).__init__(node, work_dir)
        self.wb = wb
        self.config = config

    def _create_log_entity(self, crate, log, user_ids):
        return ContextEntity(crate, log._id, properties={
            '@type': 'Action',
            'name': log.action,
            'startTime': _to_datetime(log.date),
            'agent': {
                '@id': user_ids[log.user._id]
            } if log.user is not None and log.user._id in user_ids else None,
            'object': {
                '@value': json.dumps(log.params),
            },
        })

    def _create_comment_entities(self, crate, parent_id, comment, user_ids):
        comment_config = self.config.get('comment', {})
        if not comment_config.get('enable', True):
            return []
        return super()._create_comment_entities(crate, parent_id, comment, user_ids)

    def _create_project_entities(self, crate, entity_id, node, extra_props=None):
        props = {
            '@type': 'CreativeWork',
            'name': node.title,
            'description': node.description,
            'dateCreated': _to_datetime(node.created),
            'dateModified': _to_datetime(node.modified),
            'isReplacedBy': {
                '@id': f'{entity_id}.jpcoar',
            },
            'keywords': [t.name for t in node.tags.all()],
        }
        if extra_props:
            props.update(extra_props)
        custom_props = {
            '@context': self._get_jpcoar_context(),
            '@type': 'Project',
            'dc:title': [
                {
                    '@value': node.title,
                },
            ],
            'datacite:description': {
                '@type': 'Description',
                'type': 'Other',
                'notation': [
                    {
                        '@value': node.description,
                    },
                ]
            },
            'createdAt': _to_date(node.created),
            'modifiedAt': _to_date(node.modified),
            'jpcoar:affiliation': [{
                '@type': 'Affiliation',
                'jpcoar:affiliationName': _to_localized(e, 'name', default_lang=None),
            } for e in node.affiliated_institutions.all()],
        }
        if node.license:
            custom_props.update({
                'dc:rights': ([{
                    '@id': node.license.url,
                }] if node.license.url else []) + ([{
                    '@value': fill_license_params(node.license.text, node.node_license),
                }] if node.license.text else []),
            })
        return [
            ContextEntity(crate, entity_id, properties=props),
            ContextEntity(crate, f'{entity_id}.jpcoar', properties=custom_props)
        ]

    def _create_wiki_entities(self, crate, base_path, wiki, user_ids):
        r = []
        path = os.path.join(base_path, wiki.page_name)
        comments = []
        creator = None
        latest = wiki.get_version()
        if latest is not None:
            creator = latest.user
        if self.include_users and creator._id not in user_ids:
            self._create_contributor_entities(crate, creator, user_ids)
        comments = sum([
            self._create_comment_entities(crate, path, c, user_ids)
            for c in Comment.objects.filter(root_target=Guid.load(wiki._id), deleted__isnull=True)
        ], [])
        first = wiki.versions.order_by('created').first()
        created = first.created if first is not None else None
        modified = latest.created if latest is not None else None
        r.append((path, WikiFile(wiki), comments))
        props = {
            'name': wiki.page_name,
            'encodingFormat': 'text/markdown',
            'contentSize': str(len(latest.content)) if latest is not None else None,
            'dateModified': modified.isoformat() if modified else None,
            'dateCreated': created.isoformat() if created else None,
        }
        if creator is not None and creator._id in user_ids:
            props['creator'] = user_ids[creator._id]
        crate.add_file(path, dest_path=path, properties=props)
        return r

    def _is_file_archivable(self, wb_file):
        provider = wb_file.attributes['provider']
        addons_config = self.config.get('addons', {})
        materialized = wb_file.attributes['materialized']
        logger.debug(f'is_file_archivable: {materialized}, provider={provider}, files={addons_config}')
        if provider not in addons_config:
            return False
        files = addons_config[provider].get('files', [])
        if len(files) == 0:
            files = DEFAULT_ADDONS_FILES
        files = [
            f
            for f in files
            if f['materialized'] == materialized
        ]
        if len(files) == 0:
            return True
        return files[0].get('enable', False)

    def _build_ro_crate(self, crate):
        for project in self._create_project_entities(crate, '#root', self.node, extra_props={
            'hasPart': {
                '@id': './',
            },
        }):
            crate.add(project)

        user_ids = {}
        crate.add(*self._create_creator_entities(crate, self.node.creator, user_ids))
        crate.add(*sum([self._create_contributor_entities(crate, user, user_ids) for user in self.node.contributors.all()], []))

        crate.add(*sum([
            self._create_comment_entities(crate, '#root', comment, user_ids)
            for comment in Comment.objects.filter(root_target=Guid.load(self.node._id), deleted__isnull=True)
        ], []))

        files = []
        addons_config = self.config.get('addons', {})
        for addon_app in website_settings.ADDONS_AVAILABLE:
            addon_name = addon_app.short_name
            if addon_name in addons_config and not addons_config[addon_name].get('enable', True):
                logger.info(f'Skipped {addon_name}')
                continue
            addon = self.node.get_addon(addon_name)
            if addon is None:
                continue
            if not hasattr(addon, 'serialize_waterbutler_credentials'):
                continue
            # TBD: addons
            if not addon.complete:
                continue
            logger.debug(f'ADDON(STORAGE): {addon_name}')
            for file in self.wb.get_root_files(addon_name):
                files += self._create_file_entities(crate, f'./{addon_name}', file, user_ids)

        # TBD: child nodes

        for wiki in self.node.wikis.filter(deleted__isnull=True):
            files += self._create_wiki_entities(crate, './wiki/', wiki, user_ids)

        log_config = self.config.get('log', {})
        if log_config.get('enable', True):
            for log in self.node.logs.all():
                crate.add(self._create_log_entity(crate, log, user_ids))

        for _, _, comments in files:
            crate.add(*comments)
        return crate, files

class ROCrateExtractor(object):

    def __init__(self, user, url, work_dir):
        self.user = user
        self.url = url
        self.work_dir = work_dir
        self.zip_path = None
        self._crate = None

    def ensure_node(self, node):
        node.description = self._extract_description()
        # tags
        for keyword in self.crate.get('#root').properties().get('keywords', []):
            self._ensure_tag(node, keyword)

        # TBD: restore addons
        # TBD: child nodes

        node.save()

    def ensure_folders(self, node, wb, path):
        assert path.startswith('./'), path
        folders = [
            e
            for e in self.crate.data_entities
            if e.type == 'Folder' and e.id.startswith(path) and re.match(r'^[^/]+\/$', e.id[len(path):])
        ]
        for e in folders:
            props = e.properties()
            name = _extract_value(props['name'])
            wb.get_file_by_materialized_path(f'{path[2:]}{name}/', create=True)
            self._ensure_file_metadata(node, e, f'{path[2:]}{name}/')
            self.ensure_folders(node, wb, f'{path}{name}/')

    def _extract_description(self):
        crate = self.crate
        value = _extract_default_or_jpcoar_value(
            crate,
            crate.get('#root'),
            'description',
            'datacite:description',
        )
        if isinstance(value, dict) and value.get('@type') == 'Description':
            return _extract_datacite_description(value)
        return _extract_value(value)

    @property
    def crate(self):
        if self._crate is not None:
            return self._crate
        self._crate = self._load_ro_crate()
        return self._crate

    @property
    def file_extractors(self):
        with ZipFile(self.zip_path, 'r') as zf:
            for i, file_name in enumerate(zf.namelist()):
                provider = file_name.split('/')[0]
                if provider not in ['osfstorage', 'wiki']:
                    # Skip data
                    continue
                logger.info(f'Restoring... {file_name}')
                if provider == 'wiki':
                    data_buf = io.BytesIO()
                    with zf.open(file_name, 'r') as sf:
                        shutil.copyfileobj(sf, data_buf)
                    data_buf.seek(0)
                    yield WikiExtractor(
                        self,
                        self.crate.get(file_name),
                        file_name,
                        data_buf,
                    )
                    continue
                data_path = os.path.join(self.work_dir, f'data{i}.dat')
                with zf.open(file_name, 'r') as sf:
                    with open(data_path, 'wb') as df:
                        shutil.copyfileobj(sf, df)
                yield FileExtractor(
                    self,
                    self.crate.get(file_name),
                    file_name,
                    data_path,
                )

    def _load_ro_crate(self):
        self.zip_path = os.path.join(self.work_dir, 'package.zip')
        with open(self.zip_path, 'wb') as f:
            self._download(f)
        logger.debug(f'Downloaded: {os.path.getsize(self.zip_path)}')

        file_name = 'ro-crate-metadata.json'
        with ZipFile(self.zip_path, 'r') as zf:
            with zf.open(file_name, 'r') as sf:
                logger.debug(f'ZIP-CONTENT: {file_name}')
                json_path = os.path.join(self.work_dir, file_name)
                with open(json_path, 'wb') as df:
                    shutil.copyfileobj(sf, df)
                return ROCrate(self.work_dir)

    def _download(self, file):
        resp = requests.get(self.url, stream=True)
        resp.raise_for_status()
        resp.raw.decode_content = True
        shutil.copyfileobj(resp.raw, file)

    def _ensure_tag(self, node, keyword):
        if keyword in [t.name for t in node.tags.all()]:
            return
        node.add_tags([keyword], auth=Auth(user=self.user), log=False)

    def _ensure_file_metadata(self, node, entity, file_path):
        entity_id = entity.properties()['@id']
        metadata_entities = [
            e
            for e in self.crate.get_entities()
            if e.properties().get('about', {}).get('@id', None) == entity_id and
            e.properties()['@type'] == 'FileMetadata'
        ]
        if len(metadata_entities) == 0:
            return
        logger.info(f'Metadata for {entity_id} = {metadata_entities}')
        metadata_addon = node.get_addon(SHORT_NAME)
        if metadata_addon is None:
            return
        items = [
            convert_json_ld_entity_to_metadata_item(e.properties())
            for e in metadata_entities
        ]
        metadata_addon.set_file_metadata(file_path, {
            'path': file_path,
            'folder': file_path.endswith('/'),
            'hash': '',
            'items': [i for i in items if i is not None],
        })

class FileExtractor(object):
    def __init__(self, owner, entity, file_path, data_path):
        self.owner = owner
        self.entity = entity
        self.file_path = file_path
        self.data_path = data_path

    def extract(self, node, wb):
        folder_name, file_name_ = os.path.split(self.file_path)
        file = wb.get_file_by_materialized_path(folder_name + '/')
        if file is None:
            raise IOError(f'No such directory: {folder_name}/')
        new_file = file.upload_file(self.data_path, file_name_)
        os.remove(self.data_path)
        file_node = _as_web_file(node, new_file)
        self._ensure_metadata(file_node)
        self.owner._ensure_file_metadata(node, self.entity, self.file_path)

    def _ensure_metadata(self, file_node):
        for keyword in self.entity.properties().get('keywords', []):
            self.owner._ensure_tag(file_node, keyword)
        file_node.save()

class WikiExtractor(object):
    def __init__(self, owner, entity, file_path, data_buf):
        self.owner = owner
        self.entity = entity
        self.file_path = file_path
        self.data_buf = data_buf

    def extract(self, node, wb):
        wiki_name = self.entity.properties()['name']
        WikiPage.objects.create_for_node(
            node,
            wiki_name,
            self.data_buf.getvalue().decode('utf8'),
            Auth(user=self.owner.user),
        )

def start_importing(auth, title):
    serializer = NodeSerializer(context={
        'request': RequestWrapper(auth),
    })
    node = serializer.create({
        'title': title,
        'category': 'project',
        'creator': auth.user,
    })
    return node

def _to_date(d):
    return d.date().isoformat()

def _to_datetime(d):
    return d.isoformat()

def fill_license_params(license_text, node_license):
    params = node_license.to_json()
    for k, v in params.items():
        pk = _snake_to_camel(k)
        if isinstance(v, list):
            if len(v) == 0:
                continue
            v = v[0]
        license_text = re.sub(r'{{\s*' + pk + r'\s*}}', v, license_text)
    return license_text

def to_creators_json(users):
    return json.dumps([
        _to_user_json(user)
        for user in users
    ])

def _to_user_json(user):
    return {
        'number': user.erad,
        'name_ja': ''.join([user.family_name_ja, user.middle_names_ja, user.given_name_ja]),
        'name_en': ' '.join([user.given_name, user.middle_names, user.family_name]),
    }

def _snake_to_camel(name):
    components = name.split('_')
    return components[0] + ''.join([c.capitalize() for c in components[1:]])

def _to_localized(o, prop, default_lang='en'):
    items = []
    items.append(dict([('@value', getattr(o, prop))] + ([('@language', default_lang)] if default_lang else [])))
    prop_ja = f'{prop}_ja'
    if not hasattr(o, prop_ja):
        return items
    value_ja = getattr(o, prop_ja)
    if not value_ja:
        return items
    items.append({
        '@value': value_ja,
        '@language': 'ja',
    })
    return items

def _to_localized_dict(o, prop):
    items = []
    items.append({
        '@value': o[prop],
        '@language': 'en',
    })
    prop_ja = f'{prop}_ja'
    if prop_ja not in o:
        return items
    value_ja = o[prop_ja]
    if not value_ja:
        return items
    items.append({
        '@value': value_ja,
        '@language': 'ja',
    })
    return items

def to_metadata_value(value):
    return {
        'extra': [],
        'comments': [],
        'value': value,
    }

def _extract_value(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        assert '@value' in value, value
        return value['@value']
    assert isinstance(value, list), value
    return _extract_value(value[0])

def _extract_default_or_jpcoar_value(crate, entity, default_param, jpcoar_param):
    ref = entity.properties().get('isReplacedBy', None)
    if ref is not None and '@id' in ref:
        logger.debug(f'Alternative entity: {ref}')
        ref_entity = crate.get(ref['@id'])
        if jpcoar_param in ref_entity.properties():
            return ref_entity.properties()[jpcoar_param]
    return entity.properties()[default_param]

def _extract_title(crate):
    value = _extract_default_or_jpcoar_value(
        crate,
        crate.get('#root'),
        'name',
        'dc:title',
    )
    return _extract_value(value)

def _extract_datacite_description(value):
    notation = value['notation']
    return _extract_value(notation)

@celery_app.task(bind=True, max_retries=3)
def export_project(self, user_id, node_id, config):
    user = OSFUser.load(user_id)
    node = AbstractNode.load(node_id)
    wb = WaterButlerClient(user, node)
    metadata_addon = node.get_addon(SHORT_NAME)
    schema_id = RegistrationSchema.objects.get(name=weko_settings.REGISTRATION_SCHEMA_NAME)._id
    logger.info(f'Exporting: {node_id}')
    self.update_state(state='exporting node', meta={
        'progress': 0,
        'user': user_id,
        'node': node_id,
    })
    work_dir = tempfile.mkdtemp()
    try:
        rocrate = ROCrateFactory(node, work_dir, wb, config)
        zip_path = os.path.join(work_dir, 'package.zip')
        rocrate.download_to(zip_path)
        now = datetime.now().strftime('%Y%m%d-%H%M%S')
        file_name_ = f'.rdm-project-{now}.zip'
        folder_name = 'weko'
        uploaded = wb.upload_root_file(zip_path, file_name_, folder_name)
        default_data = {
            'grdm-file:pubdate': to_metadata_value(datetime.now().date().isoformat()),
            'grdm-file:Title.ja': to_metadata_value(node.title),
            'grdm-file:Description Abstract.ja': to_metadata_value(node.description),
            'grdm-file:Creator': to_metadata_value(to_creators_json([user] if user is not None else [])),
            'grdm-file:resourcetype': to_metadata_value('dataset'),
        }
        if node.license:
            default_data.update({
                'grdm-file:Rights Resource': to_metadata_value(node.license.url),
                'grdm-file:Rights Description': to_metadata_value(
                    fill_license_params(node.license.text, node.node_license)
                ),
            })
        metadata = {
            'path': f'weko/{file_name_}',
            'folder': False,
            'hash': '',
            'items': [
                {
                    'active': True,
                    'schema': schema_id,
                    'data': default_data,
                }
            ],
        }
        metadata_addon.set_file_metadata(metadata['path'], metadata)
        self.update_state(state='finished', meta={
            'progress': 100,
            'user': user_id,
            'node': node_id,
            'file': {
                'data': uploaded.attributes,
            },
        })
        return {
            'user': user_id,
            'node': node_id,
            'file': {
                'data': uploaded.attributes,
            },
        }
    finally:
        shutil.rmtree(work_dir)

@celery_app.task(bind=True, max_retries=3)
def import_project(self, url, user_id, node_id):
    user = OSFUser.load(user_id)
    node = AbstractNode.load(node_id)
    wb = WaterButlerClient(user, node)
    work_dir = tempfile.mkdtemp()
    logger.info(f'Importing: {url} -> {node_id}, {work_dir}')
    self.update_state(state='provisioning node', meta={
        'progress': 0,
        'user': user_id,
        'node': node_id,
    })
    node.add_addon(SHORT_NAME, auth=Auth(user=user))
    try:
        extractor = ROCrateExtractor(user, url, work_dir)
        logger.info(f'RO-Crate loaded: {extractor.crate}')
        extractor.ensure_node(node)
        self.update_state(state='provisioning folders', meta={
            'progress': 10,
            'user': user_id,
            'node': node_id,
        })
        extractor.ensure_folders(node, wb, './osfstorage/')
        self.update_state(state='provisioning files', meta={
            'progress': 50,
            'user': user_id,
            'node': node_id,
        })
        for file_extractor in extractor.file_extractors:
            file_extractor.extract(node, wb)
        self.update_state(state='finished', meta={
            'progress': 100,
            'user': user_id,
            'node': node_id,
        })
        return {
            'user': user_id,
            'node': node_id,
            'crate': {
                'title': node.title,
                'description': node.description,
            },
        }
    finally:
        shutil.rmtree(work_dir)

def get_task_result(auth, task_id):
    result = celery_app.AsyncResult(task_id)
    error = None
    info = {}
    if result.failed():
        error = str(result.info)
    elif result.info is not None and auth.user._id != result.info['user']:
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)
    elif result.info is not None:
        info.update(result.info)
        if 'node' in result.info:
            node = AbstractNode.load(result.info['node'])
            info['node_url'] = node.web_url_for('view_project')
            if 'file' in result.info:
                file = result.info['file']['data']
                materialized = file['materialized'].lstrip('/')
                provider = file['provider']
                file_url = node.web_url_for('addon_view_or_download_file',
                                            path=materialized, provider=provider)
                info['file_url'] = file_url
    return {
        'state': result.state,
        'info': info,
        'error': error,
    }
