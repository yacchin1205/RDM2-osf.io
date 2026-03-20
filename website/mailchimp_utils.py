# -*- coding: utf-8 -*-

import hashlib

from django.db import transaction
import mailchimp3
from mailchimp3.mailchimpclient import MailChimpError

from framework import sentry
from framework.celery_tasks import app
from framework.celery_tasks.handlers import queued_task
from framework.auth.signals import user_confirmed
from osf.exceptions import OSFError
from osf.models import OSFUser
from website import settings


def get_mailchimp_api():
    if not settings.MAILCHIMP_API_KEY:
        raise OSFError(
            'An API key is required to connect to Mailchimp.'
        )
    return mailchimp3.MailChimp(settings.MAILCHIMP_API_KEY)


def get_list_id_from_name(list_name):
    m = get_mailchimp_api()
    mailing_lists = m.lists.all(get_all=True).get('lists', [])
    for mailing_list in mailing_lists:
        if mailing_list.get('name') == list_name:
            return mailing_list['id']
    raise OSFError('List not found.')


def get_list_name_from_id(list_id):
    m = get_mailchimp_api()
    mailing_list = m.lists.get(list_id=list_id)
    return mailing_list['name']


@queued_task
@app.task
@transaction.atomic
def subscribe_mailchimp(list_name, user_id):
    user = OSFUser.load(user_id)
    if not user:
        raise OSFError('User not found.')
    m = get_mailchimp_api()
    list_id = get_list_id_from_name(list_name=list_name)

    if user.mailchimp_mailing_lists is None:
        user.mailchimp_mailing_lists = {}

    try:
        m.lists.members.create_or_update(
            list_id=list_id,
            subscriber_hash=hashlib.md5(
                user.username.lower().encode()
            ).hexdigest(),
            data={
                'status': 'subscribed',
                'status_if_new': 'subscribed',
                'email_address': user.username,
                'merge_fields': {
                    'FNAME': user.given_name,
                    'LNAME': user.family_name,
                }
            }
        )

    except MailChimpError as error:
        sentry.log_exception()
        sentry.log_message(error)
        user.mailchimp_mailing_lists[list_name] = False
    else:
        user.mailchimp_mailing_lists[list_name] = True
    finally:
        user.save()


def unsubscribe_mailchimp(list_name, user_id, username=None, send_goodbye=True):
    """Unsubscribe a user from a mailchimp mailing list given its name.

    :param str list_name: mailchimp mailing list name
    :param str user_id: current user's id
    :param str username: current user's email (required for merged users)

    :raises: ListNotSubscribed if user not already subscribed
    """
    user = OSFUser.load(user_id)
    if not user:
        raise OSFError('User not found.')
    m = get_mailchimp_api()
    list_id = get_list_id_from_name(list_name=list_name)
    email = username or user.username
    user_hash = hashlib.md5(email.lower().encode()).hexdigest()

    # pass the error for unsubscribing a user from the mailchimp who has already been unsubscribed
    # and allow update mailing_list user field
    try:
        m.lists.members.delete(
            list_id=list_id,
            subscriber_hash=user_hash
        )
    except MailChimpError as error:
        sentry.log_exception(error)
        sentry.log_message(error)
        pass

    # Update mailing_list user field
    if user.mailchimp_mailing_lists is None:
        user.mailchimp_mailing_lists = {}
        user.save()

    user.mailchimp_mailing_lists[list_name] = False
    user.save()

@queued_task
@app.task
@transaction.atomic
def unsubscribe_mailchimp_async(list_name, user_id, username=None, send_goodbye=True):
    """ Same args as unsubscribe_mailchimp, used to have the task be run asynchronously
    """
    unsubscribe_mailchimp(list_name=list_name, user_id=user_id, username=username, send_goodbye=send_goodbye)

@user_confirmed.connect
def subscribe_on_confirm(user):
    # Subscribe user to general OSF mailing list upon account confirmation
    if settings.ENABLE_EMAIL_SUBSCRIPTIONS:
        subscribe_mailchimp(settings.MAILCHIMP_GENERAL_LIST, user._id)
