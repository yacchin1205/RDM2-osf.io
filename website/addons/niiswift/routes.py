from framework.routing import Rule, json_renderer

from website.addons.niiswift import views


api_routes = {
    'rules': [
        Rule(
            [
                '/settings/niiswift/accounts/',
            ],
            'post',
            views.swift_add_user_account,
            json_renderer,
        ),
        Rule(
            [
                '/settings/niiswift/accounts/',
            ],
            'get',
            views.swift_account_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/niiswift/settings/',
                '/project/<pid>/node/<nid>/niiswift/settings/',
            ],
            'put',
            views.swift_set_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/niiswift/settings/',
                '/project/<pid>/node/<nid>/niiswift/settings/',
            ],
            'get',
            views.swift_get_config,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/niiswift/user-auth/',
                '/project/<pid>/node/<nid>/niiswift/user-auth/',
            ],
            'put',
            views.swift_import_auth,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/niiswift/user-auth/',
                '/project/<pid>/node/<nid>/niiswift/user-auth/',
            ],
            'delete',
            views.swift_deauthorize_node,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/niiswift/buckets/',
                '/project/<pid>/node/<nid>/niiswift/buckets/',
            ],
            'get',
            views.swift_folder_list,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/niiswift/newbucket/',
                '/project/<pid>/node/<nid>/niiswift/newbucket/',
            ],
            'post',
            views.create_bucket,
            json_renderer
        ),
    ],
    'prefix': '/api/v1',
}
