from django.urls import re_path
from . import views
from admin.entitlements.views import InstitutionEntitlementList, ToggleInstitutionEntitlement, DeleteInstitutionEntitlement

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.InstitutionList.as_view(), name='list'),
    re_path(r'^institution_list/$', views.InstitutionUserList.as_view(), name='institution_list'),
    re_path(r'^create/$', views.CreateInstitution.as_view(), name='create'),
    re_path(r'^import/$', views.ImportInstitution.as_view(), name='import'),
    re_path(r'^entitlements/$', InstitutionEntitlementList.as_view(), name='entitlements'),
    # re_path(r'^(?P<institution_id>[0-9]+)/entitlements/$', InstitutionEntitlementList.as_view(), name='inst_entitlements'),
    re_path(r'^(?P<institution_id>[0-9]+)/entitlements/(?P<entitlement_id>[0-9]+)/toggle/$', ToggleInstitutionEntitlement.as_view(), name='entitlement_toggle'),
    re_path(r'^(?P<institution_id>[0-9]+)/entitlements/(?P<entitlement_id>[0-9]+)/delete/$', DeleteInstitutionEntitlement.as_view(), name='entitlement_delete'),
    re_path(r'^(?P<institution_id>[0-9]+)/$', views.InstitutionDetail.as_view(), name='detail'),
    re_path(r'^(?P<institution_id>[0-9]+)/export/$', views.InstitutionExport.as_view(), name='export'),
    re_path(r'^(?P<institution_id>[0-9]+)/delete/$', views.DeleteInstitution.as_view(), name='delete'),
    re_path(r'^(?P<institution_id>[0-9]+)/cannot_delete/$', views.CannotDeleteInstitution.as_view(), name='cannot_delete'),
    re_path(r'^(?P<institution_id>[0-9]+)/nodes/$', views.InstitutionNodeList.as_view(), name='nodes'),
    re_path(r'^(?P<institution_id>[0-9]+)/register/$', views.InstitutionalMetricsAdminRegister.as_view(), name='register_metrics_admin'),
    re_path(r'^(?P<institution_id>[0-9]+)/update_quota/$', views.UpdateQuotaUserListByInstitutionID.as_view(), name='update_quota_institution_user_list'),
    re_path(r'^(?P<institution_id>[0-9]+)/tsvexport/$', views.ExportFileTSV.as_view(), name='tsvexport'),
    re_path(r'^user_list_by_institution_id/(?P<institution_id>[0-9]+)/$', views.UserListByInstitutionID.as_view(), name='institution_user_list'),
    re_path(r'^statistical_status_default_storage/$', views.StatisticalStatusDefaultStorage.as_view(), name='statistical_status_default_storage'),
    re_path(r'^statistical_status_default_storage/tsvexport/$', views.StatisticalExportFileTSV.as_view(), name='statistical_tsvexport'),
    re_path(r'^recalculate_quota/$', views.RecalculateQuota.as_view(), name='recalculate_quota'),
    re_path(r'^(?P<institution_id>[0-9]+)/recalculate_quota/$',
        views.RecalculateQuota.as_view(), name='recalculate_quota_of_users_in_institution'),
]
