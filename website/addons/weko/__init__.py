import os

from .model import AddonWEKOUserSettings, AddonWEKONodeSettings
from .routes import api_routes
from .routes import oauth_routes
import views

MODELS = [AddonWEKONodeSettings, AddonWEKOUserSettings]
USER_SETTINGS_MODEL = AddonWEKOUserSettings
NODE_SETTINGS_MODEL = AddonWEKONodeSettings

ROUTES = [oauth_routes, api_routes]

SHORT_NAME = 'weko'
FULL_NAME = 'WEKO'

OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = []
CONFIGS = ['accounts', 'node']

CATEGORIES = ['storage']

INCLUDE_JS = {}

INCLUDE_CSS = {
    'widget': [],
    'page': [],
}

HAS_HGRID_FILES = True
GET_HGRID_DATA = views._weko_root_folder

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'weko_node_settings.mako')
USER_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'weko_user_settings.mako')
