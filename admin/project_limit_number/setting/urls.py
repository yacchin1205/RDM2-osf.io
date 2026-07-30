from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^$', views.ProjectLimitNumberSettingListView.as_view(), name='list-setting'),
    re_path(r'^create/$', views.ProjectLimitNumberSettingCreateView.as_view(), name='create-setting'),
    re_path(r'^update/$', views.ProjectLimitNumberSettingSaveAvailabilityView.as_view(), name='save-settings-availability'),
    re_path(r'^delete/(?P<setting_id>[0-9]+)/$', views.DeleteProjectLimitNumberSettingView.as_view(), name='delete-setting'),
    re_path(r'^project_limit_default/$', views.SaveProjectLimitNumberDefaultView.as_view(), name='save-project-limit-number-default'),
    re_path(r'^(?P<setting_id>[0-9]+)/$', views.ProjectLimitNumberSettingDetailView.as_view(), name='setting-detail'),
    re_path(r'^(?P<setting_id>[0-9]+)/update/$', views.UpdateProjectLimitNumberSettingView.as_view(), name='update-setting'),
    re_path(r'^user_list/$', views.UserListView.as_view(), name='user_list'),
    re_path(r'^export_user_list_csv/$', views.ExportUserListCSVView.as_view(), name='export_user_list_csv'),
]
