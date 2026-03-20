from django.urls import re_path
from . import views

app_name = 'quota_recalc'

urlpatterns = [
    re_path(r'^$', views.all_users, name='all_users'),
    re_path(r'^(?P<guid>[a-z0-9]+)/$', views.user, name='user'),
]
