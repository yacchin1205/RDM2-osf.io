from django.urls import re_path
from . import views


urlpatterns = [
    re_path(r'^$', views.InstitutionList.as_view(), name='institutions'),
    re_path(r'^(?P<institution_id>[0-9]+)/$', views.RemoveUserKeyList.as_view(), name='users'),
    re_path(r'^(?P<institution_id>[0-9]+)/delete/(?P<user_id>[0-9]+)/$', views.RemoveUserKey.as_view(), name='user_key_delete'),
]
