# -*- coding: utf-8 -*-
"""Routes for the iqbrims addon.
"""

from framework.routing import Rule, json_renderer

from . import views

# JSON endpoints
api_routes = {
    'rules': [

        #### Profile settings ###

        Rule(
            [
                '/settings/iqbrims/accounts/',
            ],
            'get',
            views.iqbrims_account_list,
            json_renderer,

        ),

        ##### Node settings #####

        Rule(
            ['/project/<pid>/iqbrims/folders/',
             '/project/<pid>/node/<nid>/iqbrims/folders/'],
            'get',
            views.iqbrims_folder_list,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/iqbrims/config/',
             '/project/<pid>/node/<nid>/iqbrims/config/'],
            'get',
            views.iqbrims_get_config,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/iqbrims/config/',
             '/project/<pid>/node/<nid>/iqbrims/config/'],
            'put',
            views.iqbrims_set_config,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/iqbrims/config/',
             '/project/<pid>/node/<nid>/iqbrims/config/'],
            'delete',
            views.iqbrims_deauthorize_node,
            json_renderer
        ),

        Rule(
            ['/project/<pid>/iqbrims/config/import-auth/',
             '/project/<pid>/node/<nid>/iqbrims/config/import-auth/'],
            'put',
            views.iqbrims_import_auth,
            json_renderer
        ),
    ],
    'prefix': '/api/v1'
}
