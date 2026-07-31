from django.urls import include, re_path
from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^external_acc_update/(?P<access_token>-?\w+)/$', views.external_acc_update, name='external_acc_update'),
    re_path(r'^institutional_storage/$', views.InstitutionalStorageView.as_view(), name='institutional_storage'),
    re_path(r'^institutional_storage/institutions/$', views.InstitutionalStorageListView.as_view(), name='institutional_storage_institutions'),
    re_path(r'^institutional_storage/institutions/(?P<institution_id>[0-9]+)/$', views.InstitutionalStorageView.as_view(), name='institutional_storage_list'),
    re_path(r'^icon/(?P<addon_name>\w+)/(?P<icon_filename>\w+\.\w+)$', views.IconView.as_view(), name='icon'),
    re_path(r'^test_connection/(?P<institution_id>[0-9]+)$', views.TestConnectionView.as_view(), name='test_connection'),
    re_path(r'^save_credentials/(?P<institution_id>[0-9]+)$', views.SaveCredentialsView.as_view(), name='save_credentials'),
    re_path(r'^credentials/(?P<institution_id>[0-9]+)$', views.FetchCredentialsView.as_view(), name='credentials'),
    re_path(r'^fetch_temporary_token/(?P<institution_id>[0-9]+)$', views.FetchTemporaryTokenView.as_view(), name='fetch_temporary_token'),
    re_path(r'^remove_auth_data_temporary/(?P<institution_id>[0-9]+)$', views.RemoveTemporaryAuthData.as_view(), name='remove_auth_data_temporary'),
    re_path(r'^usermap/(?P<institution_id>[0-9]+)$', views.UserMapView.as_view(), name='usermap'),

    re_path(r'^export_data/', include('admin.rdm_custom_storage_location.export_data.urls', namespace='export_data')),
]
