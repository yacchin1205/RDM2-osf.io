# -*- coding: utf-8 -*-

from website.oauth.models import BasicAuthProviderMixin


class SwiftProvider(BasicAuthProviderMixin):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'NII Swift'
    short_name = 'swift'

    def __init__(self, account=None, tenant_name=None, username=None, password=None):
        if username:
            username = username.lower()
        return super(SwiftProvider, self).__init__(account=account, host=tenant_name, username=username, password=password)

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.display_name if self.account else 'anonymous'
        )
