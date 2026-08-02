from django.urls import re_path
from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.InstitutionStorageList.as_view(), name='list_institution_storage'),
    re_path(r'^(?P<institution_id>[0-9]+)/update_quota/$', views.UpdateQuotaUserListByInstitutionStorageID.as_view(), name='update_quota_institution_user_list'),
    re_path(r'^user_list_by_institution_id/(?P<institution_id>[0-9]+)/$', views.UserListByInstitutionStorageID.as_view(), name='institution_user_list'),
]
