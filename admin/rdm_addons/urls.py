from django.urls import include, re_path
from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.InstitutionListView.as_view(), name='institutions'),
    re_path(r'^(?P<institution_id>-?[0-9]+)/$', views.AddonListView.as_view(), name='addons'),
    re_path(r'^allow/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/(?P<allowed>[01])$', views.AddonAllowView.as_view(), name='allow'),
    re_path(r'^force/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/(?P<forced>[01])$', views.AddonForceView.as_view(), name='force'),
    re_path(r'^icon/(?P<addon_name>\w+)/(?P<icon_filename>\w+\.\w+)$', views.IconView.as_view(), name='icon'),
    re_path(r'^api/v1/', include('admin.rdm_addons.api_v1.urls', namespace='api_v1')),
    re_path(r'^oauth/', include('admin.rdm_addons.oauth.urls', namespace='oauth')),
]
