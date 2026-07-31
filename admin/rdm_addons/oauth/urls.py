from django.urls import re_path
from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^connect/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/$', views.ConnectView.as_view(), name='connect'),
    re_path(r'^connect/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/(?P<is_custom>\w+)/$', views.ConnectView.as_view(), name='connect'),
    re_path(r'^callback/(?P<addon_name>\w+)/$', views.CallbackView.as_view(), name='callback'),
    re_path(r'^complete/(?P<addon_name>\w+)/$', views.CompleteView.as_view(), name='complete'),
    re_path(r'^accounts/(?P<external_account_id>\w+)/(?P<institution_id>-?[0-9]+)/$', views.AccountsView.as_view(), name='disconnect'),
]
