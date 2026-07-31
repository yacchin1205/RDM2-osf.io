#!/usr/bin/env python3
# encoding: utf-8

from unittest import mock
from unittest.mock import sentinel

from tests.base import OsfTestCase
from osf_tests.factories import UserFactory

import functools

from framework import sentry
from framework.sessions import set_session
from osf.models import Session


def set_sentry(status):
    def wrapper(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            with mock.patch.object(sentry, 'enabled', status):
                return func(*args, **kwargs)
        return wrapped
    return wrapper


with_sentry = set_sentry(True)
without_sentry = set_sentry(False)

@with_sentry
@mock.patch('framework.sentry.isolation_scope')
@mock.patch('framework.sentry.capture_exception')
def test_log_no_request_context(mock_capture, mock_isolation_scope):
    sentry.log_exception(sentinel.exception)
    mock_isolation_scope.return_value.__enter__.return_value.set_extra.assert_called_once_with(
        'session',
        {},
    )
    mock_capture.assert_called_once_with(sentinel.exception)


class TestSentry(OsfTestCase):

    @with_sentry
    @mock.patch('framework.sentry.isolation_scope')
    @mock.patch('framework.sentry.capture_exception')
    def test_log_not_logged_in(self, mock_capture, mock_isolation_scope):
        session_record = Session()
        set_session(session_record)
        sentry.log_exception(sentinel.exception)
        mock_isolation_scope.return_value.__enter__.return_value.set_extra.assert_called_once_with(
            'session',
            {},
        )
        mock_capture.assert_called_once_with(sentinel.exception)

    @with_sentry
    @mock.patch('framework.sentry.isolation_scope')
    @mock.patch('framework.sentry.capture_exception')
    def test_log_logged_in(self, mock_capture, mock_isolation_scope):
        user = UserFactory()
        session_record = Session()
        session_record.data['auth_user_id'] = user._id
        set_session(session_record)
        sentry.log_exception(sentinel.exception)
        mock_isolation_scope.return_value.__enter__.return_value.set_extra.assert_called_once_with(
            'session',
            {
                'auth_user_id': user._id,
            },
        )
        mock_capture.assert_called_once_with(sentinel.exception)

    @without_sentry
    @mock.patch('framework.sentry.isolation_scope')
    @mock.patch('framework.sentry.capture_exception')
    def test_log_not_enabled(self, mock_capture, mock_isolation_scope):
        sentry.log_exception(sentinel.exception)
        mock_isolation_scope.assert_not_called()
        mock_capture.assert_not_called()
