from __future__ import absolute_import

from django.urls import re_path

from admin.rdm_announcement import views

urlpatterns = [
    re_path(r'^$', views.IndexView.as_view(), name='index'),
    re_path(r'^send/$', views.SendView.as_view(), name='send'),
    re_path(r'^settings/$', views.SettingsView.as_view(), name='settings'),
    re_path(r'^update/$', views.SettingsUpdateView.as_view(), name='update'),
]
