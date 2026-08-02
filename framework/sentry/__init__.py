#!/usr/bin/env python3
import logging

from sentry_sdk import capture_exception, capture_message, init, isolation_scope
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.flask import FlaskIntegration

from framework.sessions import get_session

from website import settings

logger = logging.getLogger(__name__)

# Nothing in this module should send to Sentry if debug mode is on
#   or if Sentry isn't configured.
enabled = (not settings.DEBUG_MODE) and settings.SENTRY_DSN

if enabled:
    init(
        dsn=settings.SENTRY_DSN,
        integrations=[CeleryIntegration(), DjangoIntegration(), FlaskIntegration()],
    )


def get_session_data():
    try:
        return get_session().data
    except (RuntimeError, AttributeError):
        return {}


def log_exception(exception=None):
    if not enabled:
        logger.warning('Sentry called to log exception, but is not active')
        return None

    with isolation_scope() as scope:
        scope.set_extra('session', get_session_data())
        return capture_exception(exception)


def log_message(message, extra_data=None, level=logging.ERROR):
    if not enabled:
        logger.warning(
            'Sentry called to log message, but is not active: %s' % message
        )
        return None
    extra = {
        'session': get_session_data(),
    }
    if extra_data is not None:
        extra.update(extra_data)

    level_name = logging.getLevelName(level).lower()
    with isolation_scope() as scope:
        for key, value in extra.items():
            scope.set_extra(key, value)
        return capture_message(message, level=level_name)
