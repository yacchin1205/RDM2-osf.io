import os

from . import model
from . import routes
from . import views

MODELS = [model.AzureBlobStorageUserSettings, model.AzureBlobStorageNodeSettings]
USER_SETTINGS_MODEL = model.AzureBlobStorageUserSettings
NODE_SETTINGS_MODEL = model.AzureBlobStorageNodeSettings

ROUTES = [routes.api_routes]

SHORT_NAME = 'azureblobstorage'
FULL_NAME = 'Azure Blob Storage'


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
GET_HGRID_DATA = views.azureblobstorage_root_folder
# 1024 ** 1024  # There really shouldnt be a limit...
MAX_FILE_SIZE = 128  # MB

HERE = os.path.dirname(os.path.abspath(__file__))
NODE_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'azureblobstorage_node_settings.mako')
USER_SETTINGS_TEMPLATE = os.path.join(HERE, 'templates', 'azureblobstorage_user_settings.mako')
