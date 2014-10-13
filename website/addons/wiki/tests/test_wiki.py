# -*- coding: utf-8 -*-

# PEP8 asserts
from nose.tools import *  # noqa
from modularodm.exceptions import ValidationValueError

from tests.base import OsfTestCase, fake
from tests.factories import (
    UserFactory, NodeFactory, PointerFactory, ProjectFactory, ApiKeyFactory,
    AuthUserFactory, NodeWikiFactory,
)

from website.addons.wiki.views import serialize_wiki_toc
from website.addons.wiki.model import NodeWikiPage
from framework.auth import Auth
from framework.mongo.utils import to_mongo_key

SPECIAL_CHARACTERS = u'`~!@#$%^*()-=_+ []{}\|/?.df,;:''"'


class TestNodeWikiPageModel(OsfTestCase):

    def test_page_name_cannot_be_greater_than_100_characters(self):
        bad_name = 'a' * 101
        page = NodeWikiPage(page_name=bad_name)
        with assert_raises(ValidationValueError):
            page.save()


class TestWikiViews(OsfTestCase):

    def setUp(self):
        super(TestWikiViews, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)

    def test_wiki_url_get_returns_200(self):
        url = self.project.web_url_for('project_wiki_page', wid='home')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_wiki_url_for_pointer_returns_200(self):
        # TODO: explain how this tests a pointer
        pointer = PointerFactory(node=self.project)
        url = self.project.web_url_for('project_wiki_page', wid='home')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_wiki_content_returns_200(self):
        node = ProjectFactory()
        url = node.api_url_for('wiki_page_content', wid='somerandomid')
        res = self.app.get(url).follow()
        assert_equal(res.status_code, 200)

    def test_wiki_url_for_component_returns_200(self):
        component = NodeFactory(project=self.project)
        url = component.web_url_for('project_wiki_page', wid='home')
        res = self.app.get(url).follow()
        assert_equal(res.status_code, 200)

    def test_serialize_wiki_toc(self):
        project = ProjectFactory()
        auth = Auth(project.creator)
        NodeFactory(project=project, creator=project.creator)
        no_wiki = NodeFactory(project=project, creator=project.creator)
        project.save()

        serialized = serialize_wiki_toc(project, auth=auth)
        assert_equal(len(serialized), 2)
        no_wiki.delete_addon('wiki', auth=auth)
        serialized = serialize_wiki_toc(project, auth=auth)
        assert_equal(len(serialized), 1)

    def test_get_wiki_url_pointer_component(self):
        """Regression test for issues
        https://github.com/CenterForOpenScience/osf/issues/363 and
        https://github.com/CenterForOpenScience/openscienceframework.org/issues/574

        """
        user = UserFactory()
        pointed_node = NodeFactory(creator=user)
        project = ProjectFactory(creator=user)
        auth = Auth(user=user)
        project.add_pointer(pointed_node, auth=auth, save=True)

        serialized = serialize_wiki_toc(project, auth)
        assert_equal(
            serialized[0]['url'],
            pointed_node.web_url_for('project_wiki_page', wid='home')
        )

    def test_project_wiki_edit_post(self):
        self.project.update_node_wiki(
            'home',
            content='old content',
            auth=Auth(self.project.creator)
        )
        url = self.project.web_url_for('project_wiki_edit_post', wid='home')
        res = self.app.post(url, {'content': 'new content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        # page was updated with new content
        new_wiki = self.project.get_wiki_page('home')
        assert_equal(new_wiki.content, 'new content')

    def test_project_wiki_edit_post_with_new_wid_and_no_content(self):
        page_name = fake.catch_phrase()

        old_wiki_page_count = NodeWikiPage.find().count()
        url = self.project.web_url_for('project_wiki_edit_post', wid=page_name)
        # User submits to edit form with no content
        res = self.app.post(url, {'content': ''}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

        new_wiki_page_count = NodeWikiPage.find().count()
        # A new wiki page was created in the db
        assert_equal(new_wiki_page_count, old_wiki_page_count + 1)

        # Node now has the new wiki page associated with it
        self.project.reload()
        new_page = self.project.get_wiki_page(page_name)
        assert_is_not_none(new_page)

    def test_project_wiki_edit_post_with_new_wid_and_content(self):
        page_name, page_content = fake.catch_phrase(), fake.bs()

        old_wiki_page_count = NodeWikiPage.find().count()
        url = self.project.web_url_for('project_wiki_edit_post', wid=page_name)
        # User submits to edit form with no content
        res = self.app.post(url, {'content': page_content}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

        new_wiki_page_count = NodeWikiPage.find().count()
        # A new wiki page was created in the db
        assert_equal(new_wiki_page_count, old_wiki_page_count + 1)

        # Node now has the new wiki page associated with it
        self.project.reload()
        new_page = self.project.get_wiki_page(page_name)
        assert_is_not_none(new_page)
        # content was set
        assert_equal(new_page.content, page_content)

    def test_project_wiki_edit_post_with_non_ascii_title(self):
        # regression test for https://github.com/CenterForOpenScience/openscienceframework.org/issues/1040
        # wid doesn't exist in the db, so it will be created
        new_wid = u'øˆ∆´ƒøßå√ß'
        url = self.project.web_url_for('project_wiki_edit_post', wid=new_wid)
        res = self.app.post(url, {'content': 'new content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        wiki = self.project.get_wiki_page(new_wid)
        assert_equal(wiki.page_name, new_wid)

        # updating content should return correct url as well.
        res = self.app.post(url, {'content': 'updated content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

    def test_project_wiki_edit_post_with_special_characters(self):
        new_wid = 'title: ' + SPECIAL_CHARACTERS
        new_wiki_content = 'content: ' + SPECIAL_CHARACTERS
        url = self.project.web_url_for('project_wiki_edit_post', wid=new_wid)
        res = self.app.post(url, {'content': new_wiki_content}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        wiki = self.project.get_wiki_page(new_wid)
        assert_equal(wiki.page_name, new_wid)
        assert_equal(wiki.content, new_wiki_content)
        assert_equal(res.status_code, 200)

    def test_wiki_edit_get_new(self):
        url = self.project.web_url_for('project_wiki_edit', wid='a new page')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_wiki_edit_get_home(self):
        url = self.project.web_url_for('project_wiki_edit', wid='home')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_project_wiki_compare_returns_200(self):
        self.project.update_node_wiki('home', 'updated content', Auth(self.user))
        self.project.save()
        url = self.project.web_url_for('project_wiki_compare', wid='home', compare_id=1)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_project_wiki_compare_with_invalid_wid(self):
        url = self.project.web_url_for('project_wiki_compare', wid='this-doesnt-exist', compare_id=1)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_wiki_page_creation_strips_whitespace(self):
        # Regression test for:
        # https://github.com/CenterForOpenScience/openscienceframework.org/issues/1080
        # wid has a trailing space
        url = self.project.web_url_for('project_wiki_edit', wid='cupcake ')
        res = self.app.post(url, {'content': 'blah'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

        self.project.reload()
        wiki = self.project.get_wiki_page('cupcake')
        assert_is_not_none(wiki)


class TestWikiDelete(OsfTestCase):

    def setUp(self):
        super(TestWikiDelete, self).setUp()

        self.project = ProjectFactory(is_public=True)
        api_key = ApiKeyFactory()
        self.project.creator.api_keys.append(api_key)
        self.project.creator.save()
        self.consolidate_auth = Auth(user=self.project.creator, api_key=api_key)
        self.auth = ('test', api_key._primary_key)
        self.project.update_node_wiki('Elephants', 'Hello Elephants', self.consolidate_auth)
        self.project.update_node_wiki('Lions', 'Hello Lions', self.consolidate_auth)
        self.elephant_wiki = self.project.get_wiki_page('Elephants')
        self.lion_wiki = self.project.get_wiki_page('Lions')

    def test_project_wiki_delete(self):
        assert_in('elephants', self.project.wiki_pages_current)
        url = self.project.api_url_for(
            'project_wiki_delete',
            wid='elephants'
        )
        self.app.delete(
            url,
            auth=self.auth
        )
        self.project.reload()
        assert_not_in('elephants', self.project.wiki_pages_current)

    def test_project_wiki_delete_w_special_characters(self):
        self.project.update_node_wiki(SPECIAL_CHARACTERS, 'Hello Special Characters', self.consolidate_auth)
        self.special_characters_wiki = self.project.get_wiki_page(SPECIAL_CHARACTERS)
        assert_in(to_mongo_key(SPECIAL_CHARACTERS), self.project.wiki_pages_current)
        url = self.project.api_url_for(
            'project_wiki_delete',
            wid=SPECIAL_CHARACTERS
        )
        self.app.delete(
            url,
            auth=self.auth
        )
        self.project.reload()
        assert_not_in(to_mongo_key(SPECIAL_CHARACTERS), self.project.wiki_pages_current)


class TestWikiRename(OsfTestCase):

    def setUp(self):
        super(TestWikiRename, self).setUp()

        self.project = ProjectFactory(is_public=True)
        api_key = ApiKeyFactory()
        self.project.creator.api_keys.append(api_key)
        self.project.creator.save()
        self.consolidate_auth = Auth(user=self.project.creator, api_key=api_key)
        self.auth = ('test', api_key._primary_key)
        self.project.update_node_wiki('home', 'Hello world', self.consolidate_auth)

        self.page_name = 'page2'
        self.project.update_node_wiki(self.page_name, 'content', self.consolidate_auth)
        self.project.save()
        self.page = self.project.get_wiki_page(self.page_name)

        self.wiki = self.project.get_wiki_page('home')
        self.url = self.project.api_url_for(
            'project_wiki_rename',
            wid=self.wiki._id,
        )

    def test_rename_wiki_page_valid(self, new_name=u'away'):
        self.app.put_json(
            self.url,
            {'value': new_name, 'pk': self.page._id},
            auth=self.auth,
        )
        self.project.reload()

        old_wiki = self.project.get_wiki_page(self.page_name)
        assert_false(old_wiki)

        new_wiki = self.project.get_wiki_page(new_name)
        assert_true(new_wiki)
        assert_equal(new_wiki._id, self.page._id)
        assert_equal(new_wiki.content, self.page.content)
        assert_equal(new_wiki.version, self.page.version)

    def test_rename_wiki_page_duplicate(self):
        self.project.update_node_wiki('away', 'Hello world', self.consolidate_auth)
        new_name = 'away'

        res = self.app.put_json(
            self.url,
            {'value': new_name, 'pk': self.page._id},
            auth=self.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 409)

    def test_cannot_rename_home_page(self):
        home = self.project.get_wiki_page('home')
        res = self.app.put_json(self.url, {'value': 'homelol', 'pk': home._id}, auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_can_rename_to_a_deleted_page(self):
        self.project.delete_node_wiki(self.project, self.page, self.consolidate_auth)
        self.project.save()

        # Creates a new page
        self.project.update_node_wiki('page3', 'moarcontent', self.consolidate_auth)
        page3 = self.project.get_wiki_page('page3')
        self.project.save()

        url = self.project.api_url_for('project_wiki_rename', wid='page3')
        # Renames the wiki to the deleted page
        res = self.app.put_json(url, {'value': self.page_name, 'pk': page3._id}, auth=self.auth)
        assert_equal(res.status_code, 200)

    def test_rename_wiki_page_with_html_title(self):
        # script is not an issue since data is sanitized via bleach or mako before display.
        self.test_rename_wiki_page_valid(new_name=u'<html>hello</html')

    def test_rename_wiki_page_with_non_ascii_title(self):
        self.test_rename_wiki_page_valid(new_name=u'øˆ∆´ƒøßå√ß')

    def test_rename_wiki_page_with_special_character_title(self):
        self.test_rename_wiki_page_valid(new_name=SPECIAL_CHARACTERS)


class TestWikiLinks(OsfTestCase):

    def test_links(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        wiki = NodeWikiFactory(
            content='[[wiki2]]',
            user=user,
            node=project,
        )
        assert_in(
            project.web_url_for('project_wiki_page', wid='wiki2'),
            wiki.html(project),
        )
