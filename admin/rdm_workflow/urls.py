from django.urls import re_path

from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.WorkflowEngineInstitutionListView.as_view(), name='home'),
    re_path(r'^(?P<institution_id>\d+)/$', views.WorkflowEngineListView.as_view(), name='engine-list'),
    re_path(r'^(?P<institution_id>\d+)/(?P<engine_id>[^/]+)/edit/$', views.WorkflowEngineEditView.as_view(), name='engine-edit'),
    re_path(r'^(?P<institution_id>\d+)/(?P<engine_id>[^/]+)/keys/$', views.WorkflowEngineKeyView.as_view(), name='engine-keys'),
]
