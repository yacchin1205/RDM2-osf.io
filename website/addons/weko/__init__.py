import os

from .model import AddonWEKOUserSettings, AddonWEKONodeSettings
from .routes import api_routes
import views

MODELS = [AddonWEKONodeSettings, AddonWEKOUserSettings]
USER_SETTINGS_MODEL = AddonWEKOUserSettings
NODE_SETTINGS_MODEL = AddonWEKONodeSettings

ROUTES = [api_routes]

SHORT_NAME = 'weko'
FULL_NAME = 'WEKO'

OWNERS = ['user', 'node']

ADDED_DEFAULT = []
ADDED_MANDATORY = []

VIEWS = ['widget']
CONFIGS = ['accounts', 'node']

CATEGORIES = ['storage']

INCLUDE_JS = {
    'widget': [],
    'page': [],
    'files': [],
}

INCLUDE_CSS = {
    'widget': ['weko.css'],
    'page': [],
}

HAS_HGRID_FILES = True
GET_HGRID_DATA = views._weko_root_folder

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'weko_node_settings.mako')
USER_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'weko_user_settings.mako')
