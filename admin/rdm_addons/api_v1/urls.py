from django.urls import re_path
from . import views


urlpatterns = [
    re_path(r'^oauth/accounts/(?P<external_account_id>\w+)/(?P<institution_id>-?[0-9]+)/$', views.OAuthView.as_view(), name='oauth'),
    re_path(r'^settings/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/$', views.SettingsView.as_view(), name='settings'),
    re_path(r'^settings/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/accounts/$', views.AccountsView.as_view(), name='accounts'),
    re_path(r'^settings/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/manage/$', views.ManageView.as_view(), name='manage'),
    re_path(r'^settings/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/organization/$', views.OrganizationView.as_view(), name='organization'),
]
