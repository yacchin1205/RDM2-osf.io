import json

from unittest import mock
import pytest
from osf.models import UserExtendedData
from osf_tests.factories import AuthUserFactory
from tests.base import (fake)
from tests.base import OsfTestCase
from website.profile import views as website_view
from website.profile.views import append_idp_attr_common
from website.util import api_url_for

pytestmark = pytest.mark.django_db


class TestUserProfileExtend(OsfTestCase):

    def setUp(self):
        super(TestUserProfileExtend, self).setUp()
        self.user = AuthUserFactory()

    def test_serialize_social_with_erad(self):
        user2 = AuthUserFactory()
        self.user.social['twitter'] = 'howtopizza'
        self.user.social['profileWebsites'] = ['http://www.cos.io']
        self.user.erad = '123'
        self.user.save()
        url = api_url_for('serialize_social', uid=self.user._id)
        res = self.app.get(
            url,
            auth=user2.auth,
        )
        assert (res.json.get('twitter')) == ('howtopizza')
        assert (res.json.get('profileWebsites')) == (['http://www.cos.io'])
        assert (res.json.get('github') is None)
        assert not (res.json['editable'])
        assert (res.json.get('erad') is None)

    def test_serialize_social_with_erad_and_editable(self):
        self.user.social['twitter'] = 'howtopizza'
        self.user.social['profileWebsites'] = ['http://www.cos.io',
                                               'http://www.osf.io',
                                               'http://www.wordup.com']
        self.user.erad = '123'
        self.user.save()
        url = api_url_for('serialize_social')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        print(res)
        assert (res.json.get('twitter')) == ('howtopizza')
        assert (res.json.get('profileWebsites')) == ([
                            'http://www.cos.io',
                            'http://www.osf.io',
                            'http://www.wordup.com'
                        ])
        assert (res.json.get('erad')) == ('123')
        assert (res.json.get('github') is None)
        assert (res.json['editable'])

    def test_unserialize_names(self):
        fake_fullname_w_spaces = '    {}    '.format(fake.name())
        names = {
            'full': fake_fullname_w_spaces,
            'given': 'Tea',
            'middle': 'Gray',
            'family': 'Pot',
            'suffix': 'Ms.',
            'given_ja': 'Given name ja',
            'middle_ja': 'Middle name ja',
            'family_ja': 'Family name ja',
        }

        url = api_url_for('unserialize_names')
        res = self.app.put_json(url, names, auth=self.user.auth)
        assert (res.status_code) == (200)
        self.user.reload()

        assert (self.user.fullname) == (fake_fullname_w_spaces.strip())
        assert (self.user.given_name) == (names['given'])
        assert (self.user.middle_names) == (names['middle'])
        assert (self.user.family_name) == (names['family'])
        assert (self.user.suffix) == (names['suffix'])
        assert (self.user.given_name_ja) == (names['given_ja'])
        assert (self.user.middle_names_ja) == (names['middle_ja'])
        assert (self.user.family_name_ja) == (names['family_ja'])

    def test_serialize_account_info(self):
        url = api_url_for('serialize_account_info')

        response = self.app.get(
            url,
            auth=self.user.auth,
        )

        assert (response.status_code) == (200)
        response_data = response.body
        response_data = json.loads(response_data)
        assert (response_data['full']) == (self.user.fullname)
        assert (response_data['given']) == (self.user.given_name)
        assert (response_data['middle']) == (self.user.middle_names)
        assert (response_data['family']) == (self.user.family_name)
        assert (response_data['given_ja']) == (self.user.given_name_ja)
        assert (response_data['middle_ja']) == (self.user.middle_names_ja)
        assert (response_data['family_ja']) == (self.user.family_name_ja)
        assert (response_data['suffix']) == (self.user.suffix)
        assert (response_data['erad']) == (self.user.erad)
        assert (response_data['institution']) == (None)
        assert (response_data['department']) == (None)
        assert (response_data['institution_ja']) == (None)
        assert (response_data['department_ja']) == (None)

    def test_unserialize_account_info_initial_jobs(self):
        url = api_url_for('serialize_account_info')
        payload = {
            'full': self.user.fullname,
            'given': self.user.given_name,
            'middle': self.user.middle_names,
            'family': self.user.family_name,
            'given_ja': self.user.given_name_ja,
            'middle_ja': self.user.middle_names_ja,
            'family_ja': self.user.family_name_ja,
            'suffix': self.user.suffix,
            'erad': self.user.erad,
            'institution': 'another institution',
            'institution_ja': 'Another Institution',
            'department': 'department B',
            'department_ja': 'Department B',
            'title': '',
            'startMonth': None,
            'startYear': None,
            'endMonth': None,
            'endYear': None,
            'ongoing': False,
        }

        self.app.put_json(
            url,
            payload,
            auth=self.user.auth
        )

        self.user.reload()

        assert (self.user.fullname) == (payload['full'])
        assert (self.user.given_name) == (payload['given'])
        assert (self.user.middle_names) == (payload['middle'])
        assert (self.user.family_name) == (payload['family'])
        assert (self.user.given_name_ja) == (payload['given_ja'])
        assert (self.user.middle_names_ja) == (payload['middle_ja'])
        assert (self.user.family_name_ja) == (payload['family_ja'])
        assert (self.user.suffix) == (payload['suffix'])
        assert (self.user.erad) == (payload['erad'])
        assert (self.user.jobs[0]['institution']) == (payload['institution'])
        assert (self.user.jobs[0]['department']) == (payload['department'])
        assert (self.user.jobs[0]['institution_ja']) == (payload['institution_ja'])
        assert (self.user.jobs[0]['department_ja']) == (payload['department_ja'])
        assert (self.user.jobs[0]['title']) == (payload['title'])
        assert (self.user.jobs[0]['startMonth']) == (payload['startMonth'])
        assert (self.user.jobs[0]['startYear']) == (payload['startYear'])
        assert (self.user.jobs[0]['endMonth']) == (payload['endMonth'])
        assert (self.user.jobs[0]['endYear']) == (payload['endYear'])
        assert (self.user.jobs[0]['ongoing']) == (payload['ongoing'])

    @mock.patch('osf.models.user.OSFUser.check_spam')
    def test_unserialize_account_info_with_jobs(self, mock_check_spam):
        url = api_url_for('serialize_account_info')
        jobs = [{
            'institution': 'an institution',
            'institution_ja': 'Institution',
            'department': 'department A',
            'department_ja': 'Department A',
            'location': 'Anywhere',
            'startMonth': 'January',
            'startYear': '2001',
            'endMonth': 'March',
            'endYear': '2001',
            'ongoing': False,
        }, {
            'institution': 'another institution',
            'institution_ja': 'Another Institution',
            'department': 'department B',
            'department_ja': 'Department B',
            'location': 'Nowhere',
            'startMonth': 'January',
            'startYear': '2001',
            'endMonth': 'March',
            'endYear': '2001',
            'ongoing': False,
        }]
        self.user.jobs = jobs
        self.user.save()

        payload = {
            'full': self.user.fullname,
            'given': self.user.given_name,
            'middle': self.user.middle_names,
            'family': self.user.family_name,
            'given_ja': self.user.given_name_ja,
            'middle_ja': self.user.middle_names_ja,
            'family_ja': self.user.family_name_ja,
            'suffix': self.user.suffix,
            'erad': self.user.erad,
            'institution': 'change institution',
            'department': 'change department',
            'institution_ja': 'Change Institution',
            'department_ja': 'Change Department',
        }

        self.app.put_json(
            url,
            payload,
            auth=self.user.auth
        )

        self.user.reload()

        assert (self.user.jobs[0]['institution']) == (payload['institution'])
        assert (self.user.jobs[0]['department']) == (payload['department'])
        assert (self.user.jobs[0]['institution_ja']) == (payload['institution_ja'])
        assert (self.user.jobs[0]['department_ja']) == (payload['department_ja'])

        assert mock_check_spam.called

    def test_serialize_name(self):
        url = api_url_for('serialize_names')
        response = self.app.get(
            url,
            auth=self.user.auth,
        )

        assert (response.status_code) == (200)
        response_data = response.body
        response_data = json.loads(response_data)

        assert (response_data['full']) == (self.user.fullname)
        assert (response_data['given']) == (self.user.given_name)
        assert (response_data['middle']) == (self.user.middle_names)
        assert (response_data['family']) == (self.user.family_name)
        assert (response_data['given_ja']) == (self.user.given_name_ja)
        assert (response_data['middle_ja']) == (self.user.middle_names_ja)
        assert (response_data['family_ja']) == (self.user.family_name_ja)
        assert (response_data['suffix']) == (self.user.suffix)

    def test_unserialize_social(self):
        erad = '007'
        url = api_url_for('unserialize_social')
        payload = {
            'profileWebsites': ['http://frozen.pizza.com/reviews'],
            'twitter': 'howtopizza',
            'github': 'frozenpizzacode',
            'erad': erad
        }

        self.app.put_json(
            url,
            payload,
            auth=self.user.auth,
        )
        self.user.reload()

        self.user.social['profileWebsites'] = payload['profileWebsites']
        self.user.social['twitter'] = payload['twitter']
        self.user.social['github'] = payload['github']
        self.user.erad = payload['erad']

        assert (self.user.social['researcherId'] is None)

    def test_append_idp_attr_common(self):
        ext, created = UserExtendedData.objects.get_or_create(user=self.user)
        # update every login.
        ext.set_idp_attr(
            {
                'idp': 'identify provider',
                'eppn': 'eppn@mail.com',
                'fullname': 'fullname',
                'fullname_ja': 'fullname ja',
                'entitlement': 'Entitlement',
                'email': 'abc@mail.com',
                'organization_name': 'a organization',
                'organizational_unit': 'a organizational unit',
                'organization_name_ja': 'a organization ja',
                'organizational_unit_ja': 'a organizational unit ja',
            },
        )

        data = {
            'idp_attr': ''
        }

        self.user.save()

        append_idp_attr_common(data, self.user)

        assert (data['idp_attr']['institution']) == (self.user.ext.data['idp_attr']['organization_name'])
        assert (data['idp_attr']['department']) == (self.user.ext.data['idp_attr']['organizational_unit'])
        assert (data['idp_attr']['institution_ja']) == (self.user.ext.data['idp_attr']['organization_name_ja'])
        assert (data['idp_attr']['department_ja']) == (self.user.ext.data['idp_attr']
            ['organizational_unit_ja'])

    def test_serialize_job(self):
        job = {
            'institution': 'an institution',
            'institution_ja': 'Institution',
            'department': 'department A',
            'department_ja': 'Department A',
            'title': 'Title B',
            'startMonth': 'January',
            'startYear': '2001',
            'endMonth': 'March',
            'endYear': '2001',
            'ongoing': False,
        }
        result = website_view.serialize_job(job)
        for key, value in job.items():
            assert (result[key]) == (job[key])

    def test_serialize_school(self):
        school = {
            'institution': 'an institution',
            'department': 'a department',
            'institution_ja': 'an institution ja',
            'department_ja': 'a department ja',
            'degree': None,
            'startMonth': 1,
            'startYear': '2001',
            'endMonth': 5,
            'endYear': '2001',
            'ongoing': False,
        }
        result = website_view.serialize_school(school)
        for key, value in school.items():
            assert (result[key]) == (school[key])

    def test_unserialize_job(self):
        job = {
            'institution': 'an institution',
            'department': 'a department',
            'institution_ja': 'an institution ja',
            'department_ja': 'a department ja',
            'title': 'a title',
            'startMonth': 'January',
            'startYear': '2001',
            'endMonth': 'March',
            'endYear': '2001',
            'ongoing': False,
        }
        result = website_view.unserialize_job(job)
        for key, value in job.items():
            assert (result[key]) == (job[key])

    def test_unserialize_school(self):
        school = {
            'institution': 'an institution',
            'department': 'a department',
            'institution_ja': 'an institution ja',
            'department_ja': 'a department ja',
            'degree': None,
            'startMonth': 1,
            'startYear': '2001',
            'endMonth': 5,
            'endYear': '2001',
            'ongoing': False,
        }
        result = website_view.unserialize_school(school)
        for key, value in school.items():
            assert (result[key]) == (school[key])
