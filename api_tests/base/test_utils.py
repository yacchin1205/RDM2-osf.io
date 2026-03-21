# -*- coding: utf-8 -*-
import mock  # noqa
import unittest
import pytest
from osf.models import ProjectLimitNumberSetting, AbstractNode, ProjectLimitNumberDefault
from osf_tests.factories import UserFactory, InstitutionFactory
from osf.models.project_limit_number_setting_attribute import ProjectLimitNumberSettingAttribute
from osf.models.project_limit_number_template import ProjectLimitNumberTemplate
from osf.models.project_limit_number_template_attribute import ProjectLimitNumberTemplateAttribute
from rest_framework.exceptions import ValidationError
from api.base import utils as api_utils

from framework.status import push_status_message


class TestTruthyFalsy:
    """Check the truthy/falsy contract used by api.base.utils."""

    def test_truthy(self):
        for value in ('t', 'T', 'true', 'True', 'TRUE', '1', 1, True, 'on', 'ON', 'On', 'y', 'Y', 'YES', 'yes'):
            assert api_utils.is_truthy(value)
        for value in ('f', 'F', 'false', 'False', 'FALSE', '0', 0, 0.0, False, 'off', 'OFF', 'Off', 'n', 'N', 'NO', 'no'):
            assert not api_utils.is_truthy(value)

    def test_falsy(self):
        for value in ('f', 'F', 'false', 'False', 'FALSE', '0', 0, 0.0, False, 'off', 'OFF', 'Off', 'n', 'N', 'NO', 'no'):
            assert api_utils.is_falsy(value)
        for value in ('t', 'T', 'true', 'True', 'TRUE', '1', 1, True, 'on', 'ON', 'On', 'y', 'Y', 'YES', 'yes'):
            assert not api_utils.is_falsy(value)


class TestIsDeprecated(unittest.TestCase):

    def setUp(self):
        super(TestIsDeprecated, self).setUp()
        self.min_version = '2.0'
        self.max_version = '2.5'

    def test_is_deprecated(self):
        request_version = '2.6'
        is_deprecated = api_utils.is_deprecated(
            request_version, self.min_version, self.max_version)
        assert is_deprecated is True

    def test_is_not_deprecated(self):
        request_version = '2.5'
        is_deprecated = api_utils.is_deprecated(
            request_version, self.min_version, self.max_version)
        assert is_deprecated is False

    def test_is_deprecated_larger_versions(self):
        request_version = '2.10'
        is_deprecated = api_utils.is_deprecated(
            request_version, self.min_version, self.max_version
        )
        assert is_deprecated is True


class TestFlaskDjangoIntegration:
    def test_push_status_message_no_response(self):
        status_message = 'This is a message'
        statuses = ['info', 'warning', 'warn', 'success', 'danger', 'default']
        for status in statuses:
            try:
                push_status_message(status_message, kind=status)
            except BaseException:
                assert False

    def test_push_status_message_expected_error(self):
        status_message = 'This is a message'
        try:
            push_status_message(status_message, kind='error')
            assert False
        except ValidationError as e:
            assert e.detail[0] == status_message, 'push_status_message() should have passed along the message with the Exception.'
        except RuntimeError:
            assert False
        except BaseException:
            assert False

    @mock.patch('framework.status.session')
    def test_push_status_message_unexpected_error(self, mock_sesh):
        status_message = 'This is a message'
        exception_message = 'this is some very unexpected problem'
        mock_get = mock.Mock(side_effect=RuntimeError(exception_message))
        mock_data = mock.Mock()
        mock_data.attach_mock(mock_get, 'get')
        mock_sesh.attach_mock(mock_data, 'data')
        try:
            push_status_message(status_message, kind='error')
            assert False
        except ValidationError:
            assert False
        except RuntimeError as e:
            assert str(e) == exception_message, 'push_status_message() should have re-raised the original RuntimeError with the original message.'
        except BaseException:
            assert False


@pytest.mark.django_db
class TestCheckUserCanCreateProject:

    @pytest.fixture
    def user(self):
        return UserFactory()

    @pytest.fixture
    def institution(self):
        return InstitutionFactory()

    def test_without_user_cannot_create(self):
        assert not api_utils.check_user_can_create_project(None)

    def test_user_without_institution_can_create(self, user):
        assert api_utils.check_user_can_create_project(user)

    def test_user_with_no_limit(self, user, institution):
        user.affiliated_institutions.add(institution)

        ProjectLimitNumberDefault.objects.create(
            institution=institution,
            project_limit_number=-1
        )

        assert api_utils.check_user_can_create_project(user)

    def test_user_under_limit(self, user, institution):
        user.affiliated_institutions.add(institution)

        ProjectLimitNumberDefault.objects.create(
            institution=institution,
            project_limit_number=5
        )

        with mock.patch.object(AbstractNode.objects, 'filter') as mock_filter:
            mock_filter.return_value.count.return_value = 3
            assert api_utils.check_user_can_create_project(user)

    def test_user_at_limit(self, user, institution):
        user.affiliated_institutions.add(institution)

        ProjectLimitNumberDefault.objects.create(
            institution=institution,
            project_limit_number=5
        )

        with mock.patch.object(AbstractNode.objects, 'filter') as mock_filter:
            mock_filter.return_value.count.return_value = 5
            assert not api_utils.check_user_can_create_project(user)

    def test_user_matches_setting_condition(self, user, institution):
        user.affiliated_institutions.add(institution)
        template = ProjectLimitNumberTemplate.objects.create(template_name='Demo')
        template_attribute = ProjectLimitNumberTemplateAttribute.objects.create(
            template=template, attribute_name='sn', setting_type=1
        )
        setting = ProjectLimitNumberSetting.objects.create(
            template=template,
            institution=institution,
            project_limit_number=10,
            is_availability=True,
            priority=1,
        )
        ProjectLimitNumberSettingAttribute.objects.create(
            setting=setting, attribute=template_attribute, attribute_value='demo'
        )

        with mock.patch('api.base.utils.check_logic_condition') as mock_check:
            mock_check.return_value = True
            with mock.patch.object(AbstractNode.objects, 'filter') as mock_filter:
                # Can't create project
                mock_filter.return_value.count.return_value = 10
                assert not api_utils.check_user_can_create_project(user)
                # Can create project
                mock_filter.return_value.count.return_value = 9
                assert api_utils.check_user_can_create_project(user)

    def test_user_no_matching_setting(self, user, institution):
        user.affiliated_institutions.add(institution)

        ProjectLimitNumberDefault.objects.create(
            institution=institution, project_limit_number=5
        )
        template = ProjectLimitNumberTemplate.objects.create(template_name='Demo')
        template_attribute = ProjectLimitNumberTemplateAttribute.objects.create(
            template=template, attribute_name='sn', setting_type=1
        )
        setting = ProjectLimitNumberSetting.objects.create(
            template=template,
            institution=institution,
            project_limit_number=10,
            is_availability=True,
            priority=1,
        )
        ProjectLimitNumberSettingAttribute.objects.create(
            setting=setting, attribute=template_attribute, attribute_value='demo'
        )

        with mock.patch('api.base.utils.check_logic_condition') as mock_check:
            mock_check.return_value = False
            with mock.patch.object(AbstractNode.objects, 'filter') as mock_filter:
                # can't create project
                mock_filter.return_value.count.return_value = 5
                assert not api_utils.check_user_can_create_project(user)
                # can create project
                mock_filter.return_value.count.return_value = 4
                assert api_utils.check_user_can_create_project(user)
