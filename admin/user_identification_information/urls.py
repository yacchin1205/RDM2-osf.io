from django.urls import re_path

from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^institutions/$', views.UserIdentificationInstitutionListView.as_view(),
        name='user_identification_institutions'),
    re_path(r'^institutions/(?P<institution_id>[0-9]+)/$', views.UserIdentificationListView.as_view(),
        name='user_identification_list'),
    re_path(r'^institutions/(?P<institution_id>[0-9]+)/csvexport/$', views.ExportFileCSVView.as_view(),
        name='user_identification_export_csv'),
    re_path(r'^(?P<guid>[a-z0-9]+)/$', views.UserIdentificationDetailView.as_view(),
        name='user_identification_detail'),
]
