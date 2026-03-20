#!/usr/bin/env python3
# encoding: utf-8

import logging
from typing import Literal

from sentry_sdk import capture_exception, capture_message, configure_scope, init, isolation_scope
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.flask import FlaskIntegration

from framework.sessions import get_session
from website import settings

logger = logging.getLogger(__name__)
enabled = (not settings.DEBUG_MODE) and settings.SENTRY_DSN

LOG_LEVEL_MAP: dict[int, Literal['debug', 'info', 'warning', 'error', 'critical']] = {
    logging.DEBUG: 'debug',
    logging.INFO: 'info',
    logging.WARNING: 'warning',
    logging.ERROR: 'error',
    logging.CRITICAL: 'critical',
}


class CompatSentry:
    def __init__(self):
        self._initialized = False

    def init_app(self, app=None, app_name='web'):
        if not enabled:
            return None
        if not self._initialized:
            init(
                dsn=settings.SENTRY_DSN,
                integrations=[CeleryIntegration(), DjangoIntegration(), FlaskIntegration()],
                release=settings.VERSION,
            )
            self._initialized = True
        if app_name:
            with configure_scope() as scope:
                scope.set_tag('App', app_name)
        return None

    def captureException(self, extra=None, exception=None):
        if not enabled:
            logger.warning('Sentry called to log exception, but is not active')
            return None
        self.init_app()
        with isolation_scope() as scope:
            for key, value in (extra or {}).items():
                scope.set_extra(key, value)
            return capture_exception(exception)

    def captureMessage(self, message, extra=None, level=logging.ERROR):
        if not enabled:
            logger.warning('Sentry called to log message, but is not active: %s', message)
            return None
        self.init_app()
        with isolation_scope() as scope:
            for key, value in (extra or {}).items():
                scope.set_extra(key, value)
            return capture_message(message, level=LOG_LEVEL_MAP.get(level, 'error'))


sentry = CompatSentry()


def get_session_data():
    try:
        return get_session().data
    except (RuntimeError, AttributeError):
        return {}


def log_exception(exception=None, skip_session=False):
    extra = {
        'session': {} if skip_session else get_session_data(),
    }
    return sentry.captureException(extra=extra, exception=exception)


def log_message(message, skip_session=False, extra_data=None, level=logging.ERROR):
    extra = {
        'session': {} if skip_session else get_session_data(),
    }
    if extra_data is not None:
        extra.update(extra_data)
    return sentry.captureMessage(message, extra=extra, level=level)
