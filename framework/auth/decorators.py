# -*- coding: utf-8 -*-

import time
import httplib
import functools

from flask import request

from framework.auth import cas
from framework.auth import signing
from framework.flask import redirect
from framework.exceptions import HTTPError
from .core import Auth


# TODO [CAS-10][OSF-7566]: implement long-term fix for URL preview/prefetch
def block_bing_preview(func):
    """
    This decorator is a temporary fix to prevent BingPreview from pre-fetching confirmation links.
    """

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        user_agent = request.headers.get('User-Agent')
        if user_agent and ('BingPreview' in user_agent or 'MSIE 9.0' in user_agent):
            return HTTPError(httplib.FORBIDDEN, data={'message_long': 'Internet Explorer 9 and BingPreview cannot be used to access this page for security reasons. Please use another browser. If this should not have occurred and the issue persists, please report it to <a href="mailto: support@osf.io">support@osf.io</a>.'})
        return func(*args, **kwargs)

    return wrapped


def collect_auth(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        kwargs['auth'] = Auth.from_kwargs(request.args.to_dict(), kwargs)
        return func(*args, **kwargs)

    return wrapped


def must_be_confirmed(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        from osf.models import OSFUser

        user = OSFUser.load(kwargs['uid'])
        if user is not None:
            if user.is_confirmed:
                return func(*args, **kwargs)
            else:
                raise HTTPError(httplib.BAD_REQUEST, data={
                    'message_short': 'Account not yet confirmed',
                    'message_long': 'The profile page could not be displayed as the user has not confirmed the account.'
                })
        else:
            raise HTTPError(httplib.NOT_FOUND)

    return wrapped


def email_required(func):
    """Require that user has email."""
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        auth = Auth.from_kwargs(request.args.to_dict(), kwargs)
        if auth.logged_in:
            auth.user.update_date_last_access()
            if auth.user.have_email:
                setup_groups(auth)
                return func(*args, **kwargs)
            else:
                from website.util import web_url_for
                return redirect(web_url_for('user_account_email'))
        else:
            return func(*args, **kwargs)

    return wrapped


def must_be_logged_in(func):
    """Require that user be logged in. Modifies kwargs to include the current
    user.

    """
    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        auth = Auth.from_kwargs(request.args.to_dict(), kwargs)
        kwargs['auth'] = auth
        if auth.logged_in:
            auth.user.update_date_last_access()
            if auth.user.have_email:
                setup_groups(auth)
                return func(*args, **kwargs)
            else:
                from website.util import web_url_for
                return redirect(web_url_for('user_account_email'))
        else:
            return redirect(cas.get_login_url(request.url))

    return wrapped


def must_be_logged_in_without_checking_email(func):
    """Require that user be logged in. Modifies kwargs to include the current
    user without checking email existence.

    """
    @functools.wraps(func)
    def wrapped(*args, **kwargs):

        kwargs['auth'] = Auth.from_kwargs(request.args.to_dict(), kwargs)
        if kwargs['auth'].logged_in:
            kwargs['auth'].user.update_date_last_access()
            return func(*args, **kwargs)
        else:
            return redirect(cas.get_login_url(request.url))

    return wrapped


def setup_groups(auth):
    user = auth.user
    if user.groups_initialized:
        return
    #create_or_join_group_projects(user)
    #leave_group_projects(auth)
    #user.groups_initialized = True
    #user.save()


def get_group_node(groupname):
    from website.project.model import Node
    from modularodm import Q
    try:
        node = Node.find_one(Q('group', 'eq', groupname))
        return node
    except:
        return None

def is_group_admin(user, groupname):
    if groupname in user.groups_admin:
        return True
    else:
        return False

def is_node_admin(node, user):
    return node.has_permission(user, 'admin', check_parent=False)

def create_group_project(user, groupname):
    from website.project.model import Node
    node = Node(title = groupname,
                category = "project",
                description = groupname + " (created automatically)", #TODO
                group = groupname,
                creator = user)
    node.save()

def create_or_join_group_projects(user):
    from website.util.permissions import CREATOR_PERMISSIONS, DEFAULT_CONTRIBUTOR_PERMISSIONS
    for groupname in user.groups:
        group_admin = is_group_admin(user, groupname)
        node = get_group_node(groupname)
        if node is not None:  # exists
            if node.is_deleted == True and group_admin:
                node.is_deleted = False   # re-enabled
                node.save()
            if node.is_contributor(user):
                node_admin = is_node_admin(node, user)
                if node_admin:
                    if not group_admin:
                        node.set_permissions(user,
                                             DEFAULT_CONTRIBUTOR_PERMISSIONS,
                                             save=True)
                else:
                    if group_admin:
                        node.set_permissions(user, CREATOR_PERMISSIONS,
                                             save=True)
            elif group_admin:
                node.add_contributor(user, log=True, save=True,
                                     permissions=CREATOR_PERMISSIONS)
            else:  # not admin
                node.add_contributor(user, log=True, save=True)
        elif group_admin:  # not exist && is admin
            create_group_project(user, groupname)

def leave_group_projects(auth):
    user = auth.user
    from website.project.model import Node
    nodes = Node.find_for_user(user)
    for node in nodes:
        if node.group is None:
            continue  # skip
        if user.groups is None:
            continue  # skip
        if node.group in user.groups:
            continue  # skip
        if not user._id in node.contributors:
            continue  # skip
        if not is_node_admin(node, user):
            node.remove_contributor(user, auth=auth, log=True)
            ### node.remove_contributor() includes node.save()
            continue  # next
        admins = list(node.get_admin_contributors(node.contributors))
        len_admins = len(admins)
        if len_admins > 1:
            node.remove_contributor(user, auth=auth, log=True)
            ### node.remove_contributor() includes node.save()
            continue  # next
        ### The user is last admin.
        ### len(node.contributors) may not be 1.
        node.remove_node(auth)  # node.is_deleted = True


def must_be_signed(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if request.method in ('GET', 'DELETE'):
            data = request.args
        else:
            data = request.get_json()

        try:
            sig = data['signature']
            payload = signing.unserialize_payload(data['payload'])
            exp_time = payload['time']
        except (KeyError, ValueError):
            raise HTTPError(httplib.BAD_REQUEST, data={
                'message_short': 'Invalid payload',
                'message_long': 'The request payload could not be deserialized.'
            })

        if not signing.default_signer.verify_payload(sig, payload):
            raise HTTPError(httplib.UNAUTHORIZED)

        if time.time() > exp_time:
            raise HTTPError(httplib.BAD_REQUEST, data={
                'message_short': 'Expired',
                'message_long': 'Signature has expired.'
            })

        kwargs['payload'] = payload
        return func(*args, **kwargs)
    return wrapped
