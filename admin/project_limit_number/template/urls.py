from django.urls import re_path
from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.ProjectLimitNumberTemplateListView.as_view(), name='list-template'),
    re_path(r'^create/$', views.ProjectLimitNumberTemplatesViewCreate.as_view(), name='create-template'),
    re_path(r'^update/$', views.ProjectLimitNumberTemplatesSettingSaveAvailabilityView.as_view(), name='save-templates-availability'),
    re_path(r'^(?P<template_id>[0-9]+)/$', views.ProjectLimitNumberTemplatesViewUpdate.as_view(), name='detail-template'),
    re_path(r'^(?P<template_id>[0-9]+)/update/$', views.UpdateProjectLimitNumberTemplatesSettingView.as_view(), name='update-template'),
    re_path(r'^delete/(?P<template_id>[0-9]+)/$', views.DeleteProjectLimitNumberTemplatesSettingView.as_view(), name='delete-template'),
]
