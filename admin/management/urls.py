from __future__ import absolute_import

from django.urls import re_path

from admin.management import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.ManagementCommands.as_view(), name='commands'),
    re_path(r'^waffle_flag', views.WaffleFlag.as_view(), name='waffle_flag')
]
