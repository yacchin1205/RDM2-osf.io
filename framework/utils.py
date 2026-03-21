from __future__ import absolute_import
import re
import pytz
import time
from datetime import datetime
from bleach.css_sanitizer import CSSSanitizer, ALLOWED_CSS_PROPERTIES
from bleach.sanitizer import Cleaner, ALLOWED_ATTRIBUTES, ALLOWED_PROTOCOLS, ALLOWED_TAGS
from django.utils import timezone
from werkzeug.utils import secure_filename as werkzeug_secure_filename


def iso8601format(dt):
    """Given a datetime object, return an associated ISO-8601 string"""
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ') if dt else ''


def secure_filename(filename):
    """Return a secure version of a filename.

    Uses ``werkzeug.utils.secure_filename``, but explicitly allows for leading
    underscores.

    :param filename str: A filename to sanitize

    :return: Secure version of filename
    """
    secure = werkzeug_secure_filename(filename)

    # Check for leading underscores, and add them back in
    try:
        secure = re.search('^_+', filename).group() + secure
    except AttributeError:
        pass

    return secure


def sanitize_html(
    text,
    tags=ALLOWED_TAGS,
    attributes=ALLOWED_ATTRIBUTES,
    protocols=ALLOWED_PROTOCOLS,
    strip=False,
    styles=ALLOWED_CSS_PROPERTIES,
    strip_comments=True,
    filters=None,
):
    css_sanitizer = None
    if styles is not None:
        css_sanitizer = CSSSanitizer(allowed_css_properties=styles)
    cleaner = Cleaner(
        tags=tags,
        attributes=attributes,
        protocols=protocols,
        strip=strip,
        strip_comments=strip_comments,
        css_sanitizer=css_sanitizer,
        filters=filters,
    )
    return cleaner.clean(text)


def get_timestamp():
    return int(time.time())


def throttle_period_expired(timestamp, throttle):
    if not timestamp:
        return True
    elif isinstance(timestamp, datetime):
        if timestamp.tzinfo:
            return (timezone.now() - timestamp).total_seconds() > throttle
        else:
            return (timezone.now() - timestamp.replace(tzinfo=pytz.utc)).total_seconds() > throttle
    else:
        return (get_timestamp() - timestamp) > throttle
