from django.urls import re_path

from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.UserIdentificationAdminListView.as_view(),
        name='user_identification_list'),
    re_path(r'^csvexport/$', views.ExportFileCSVAdminView.as_view(),
        name='user_identification_export_csv'),
    re_path(r'^(?P<guid>[a-z0-9]+)/$', views.UserIdentificationDetailAdminView.as_view(),
        name='user_identification_detail'),
]
