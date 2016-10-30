from framework.routing import Rule, json_renderer
from website.routes import OsfWebRenderer

from . import views

oauth_routes = {
    'rules': [
        Rule(
            '/connect/weko/<repoid>/',
            'get',
            views.weko_oauth_connect,
            json_renderer,
        ),
        Rule(
            '/callback/weko/<repoid>/',
            'get',
            views.weko_oauth_callback,
            OsfWebRenderer('util/oauth_complete.mako', trust=False),
        ),
    ],
    'prefix': '/oauth'
  }

api_routes = {
    'rules': [
        Rule(
            '/settings/weko/',
            'get',
            views.weko_user_config_get,
            json_renderer,
        ),
        Rule(
            '/settings/weko/accounts/',
            'post',
            views.weko_add_user_account,
            json_renderer,
        ),
        Rule(
            '/settings/weko/accounts/',
            'get',
            views.weko_account_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/settings/',
                '/project/<pid>/node/<nid>/weko/settings/',
            ],
            'get',
            views.weko_get_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/settings/',
                '/project/<pid>/node/<nid>/weko/settings/',
            ],
            'post',
            views.weko_set_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/user-auth/',
                '/project/<pid>/node/<nid>/weko/user-auth/',
            ],
            'put',
            views.weko_import_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/user-auth/',
                '/project/<pid>/node/<nid>/weko/user-auth/',
            ],
            'delete',
            views.weko_deauthorize_node,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/list-datasets/',
                '/project/<pid>/node/<nid>/weko/list-datasets/',
            ],
            'post',
            views.weko_get_datasets,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/hgrid/root/',
                '/project/<pid>/node/<nid>/weko/hgrid/root/',
            ],
            'get',
            views.weko_root_folder,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/publish/',
                '/project/<pid>/node/<nid>/weko/publish/',
            ],
            'put',
            views.weko_publish_dataset,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/weko/widget/',
                '/project/<pid>/node/<nid>/weko/widget/',
            ],
            'get',
            views.weko_widget,
            OsfWebRenderer('../addons/weko/templates/weko_widget.mako', trust=False),
        ),
        Rule(
            [
                '/project/<pid>/weko/widget/contents/',
                '/project/<pid>/node/<nid>/weko/widget/contents/',
            ],
            'get',
            views.weko_get_widget_contents,
            json_renderer,
        ),
    ],
    'prefix': '/api/v1'
}
