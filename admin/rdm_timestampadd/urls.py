from django.urls import re_path
from . import views


urlpatterns = [
    re_path(r'^$', views.InstitutionList.as_view(), name='institutions'),
    re_path(r'^(?P<institution_id>[0-9]+)/nodes/$', views.InstitutionNodeList.as_view(), name='nodes'),
    re_path(r'^(?P<institution_id>[0-9]+)/nodes/csvexport/$', views.InstitutionNodeListExportCsv.as_view(), name='csvexport'),
    re_path(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/$',
        views.TimeStampAddList.as_view(), name='timestamp_add'),
    re_path(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/verify/$',
        views.VerifyTimestamp.as_view(), name='verify'),
    re_path(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/addtimestamp/add_timestamp_data/$',
        views.AddTimestamp.as_view(), name='add_timestamp_data'),
    re_path(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/addtimestamp/cancel_task/$',
        views.CancelTask.as_view(), name='cancel_task'),
    re_path(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/addtimestamp/task_status/$',
        views.TaskStatus.as_view(), name='task_status'),
    re_path(r'^(?P<institution_id>[0-9]+)/nodes/(?P<guid>[a-z0-9]+)/addtimestamp/download_errors/$',
        views.DownloadErrors.as_view(), name='download_errors'),
]
