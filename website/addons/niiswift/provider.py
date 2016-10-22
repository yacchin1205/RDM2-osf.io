from website.addons.niiswift.serializer import SwiftSerializer

class SwiftProvider(object):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'NII Swift'
    short_name = 'niiswift'
    serializer = SwiftSerializer

    def __init__(self, account=None):
        super(SwiftProvider, self).__init__()

        # provide an unauthenticated session by default
        self.account = account

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.provider_id if self.account else 'anonymous'
        )
