from django.urls import re_path
from . import views


urlpatterns = [
    re_path(r'^erad$', views.ERadRecordDashboard.as_view(), name='e-rad-records'),
    re_path(r'^erad/records', views.ERadRecords.as_view(), name='update-e-rad-records'),
]
