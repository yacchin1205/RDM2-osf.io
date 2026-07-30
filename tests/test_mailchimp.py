from hashlib import md5
from unittest import mock

import pytest
from mailchimp3.mailchimpclient import MailChimpError

from framework.celery_tasks import handlers
from osf.exceptions import OSFError
from osf_tests.factories import UserFactory
from tests.base import OsfTestCase
from website import mailchimp_utils


@pytest.mark.enable_enqueue_task
class TestMailChimpHelpers(OsfTestCase):

    def setUp(self, *args, **kwargs):
        super(TestMailChimpHelpers, self).setUp(*args, **kwargs)
        with self.context:
            handlers.celery_before_request()

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_get_list_id_from_name(self, mock_get_mailchimp_api):
        list_name = 'foo'
        with mock.patch.dict(
            mailchimp_utils.settings.MAILCHIMP_LIST_MAP,
            {list_name: '12345'},
            clear=True,
        ):
            assert mailchimp_utils.get_list_id_from_name(list_name) == '12345'
        mock_get_mailchimp_api.assert_not_called()

    def test_get_list_id_from_unknown_name(self):
        with mock.patch.dict(
            mailchimp_utils.settings.MAILCHIMP_LIST_MAP,
            {},
            clear=True,
        ):
            with pytest.raises(OSFError, match='List not found'):
                mailchimp_utils.get_list_id_from_name('unknown')

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_get_list_name_from_id(self, mock_get_mailchimp_api):
        list_id = '12345'
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.get.return_value = {'id': list_id, 'name': 'foo'}
        list_name = mailchimp_utils.get_list_name_from_id(list_id)
        mock_client.lists.get.assert_called_with(list_id=list_id)
        assert list_name == 'foo'

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_subscribe_called_with_correct_arguments(self, mock_get_mailchimp_api):
        list_name = 'foo'
        list_id = '12345'
        user = UserFactory()
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        with mock.patch.dict(
            mailchimp_utils.settings.MAILCHIMP_LIST_MAP,
            {list_name: list_id},
            clear=True,
        ):
            mailchimp_utils.subscribe_mailchimp(list_name, user._id)
            handlers.celery_teardown_request()
        mock_client.lists.members.create_or_update.assert_called_with(
            list_id=list_id,
            subscriber_hash=md5(user.username.lower().encode()).hexdigest(),
            data={
                'status': 'subscribed',
                'status_if_new': 'subscribed',
                'email_address': user.username,
                'merge_fields': {
                    'FNAME': user.given_name,
                    'LNAME': user.family_name,
                },
            },
        )

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_subscribe_fake_email_does_not_throw_validation_error(self, mock_get_mailchimp_api):
        list_name = 'foo'
        user = UserFactory(username='fake@fake.com')
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.members.create_or_update.side_effect = MailChimpError
        with mock.patch.dict(
            mailchimp_utils.settings.MAILCHIMP_LIST_MAP,
            {list_name: '12345'},
            clear=True,
        ):
            mailchimp_utils.subscribe_mailchimp(list_name, user._id)
            handlers.celery_teardown_request()
        user.reload()
        assert not user.mailchimp_mailing_lists[list_name]

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_unsubscribe_called_with_correct_arguments(self, mock_get_mailchimp_api):
        list_name = 'foo'
        list_id = '12345'
        user = UserFactory()
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        with mock.patch.dict(
            mailchimp_utils.settings.MAILCHIMP_LIST_MAP,
            {list_name: list_id},
            clear=True,
        ):
            mailchimp_utils.unsubscribe_mailchimp_async(list_name, user._id)
            handlers.celery_teardown_request()
        mock_client.lists.members.delete.assert_called_with(
            list_id=list_id,
            subscriber_hash=md5(user.username.lower().encode()).hexdigest(),
        )
