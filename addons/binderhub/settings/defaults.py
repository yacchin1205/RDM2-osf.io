DEFAULT_BINDER_URL = 'https://binder.cs.rcos.nii.ac.jp'

BINDERHUB_OAUTH_CLIENT = dict(
    client_id='AAAA',
    client_secret='BBBB',
    authorize_url='http://192.168.168.167:8585/api/oauth2/authorize',
    token_url='http://192.168.168.167:8585/api/oauth2/token',
    services_url='http://192.168.168.167:8585/api/services',
    scope=['identity'],
)

JUPYTERHUB_OAUTH_CLIENTS = {
    'http://localhost:8585/': dict(
        admin_api_token='d43ab6030a1b46b39d3233d7fe1843ad',
        client_id='AAAA',
        client_secret='BBBB',
        authorize_url='http://192.168.168.167:12000/hub/api/oauth2/authorize',
        token_url='http://192.168.168.167:12000/hub/api/oauth2/token',
        api_url='http://192.168.168.167:12000/hub/api/',
        scope=['identity'],
    )
}
