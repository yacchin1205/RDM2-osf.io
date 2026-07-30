from django.urls import include, re_path
from django.contrib import admin
from admin.base.settings import ADMIN_BASE, DEBUG
from admin.base import views

base_pattern = '^{}'.format(ADMIN_BASE)

urlpatterns = [
    ### ADMIN ###
    re_path(
        base_pattern,
        include([
            re_path(r'^$', views.home, name='home'),
            re_path(r'^admin/', admin.site.urls),
            re_path(r'^asset_files/', include('admin.asset_files.urls', namespace='asset_files')),
            re_path(r'^banners/', include('admin.banners.urls', namespace='banners')),
            re_path(r'^brands/', include('admin.brands.urls', namespace='brands')),
            re_path(r'^spam/', include('admin.spam.urls', namespace='spam')),
            re_path(r'^institutions/', include('admin.institutions.urls', namespace='institutions')),
            re_path(r'^entitlements/', include('admin.entitlements.urls', namespace='entitlements')),
            re_path(r'^quota_recalc/', include('admin.quota_recalc.urls', namespace='quota_recalc')),
            re_path(r'^preprint_providers/', include('admin.preprint_providers.urls', namespace='preprint_providers')),
            re_path(r'^collection_providers/', include('admin.collection_providers.urls', namespace='collection_providers')),
            re_path(r'^registration_providers/', include('admin.registration_providers.urls', namespace='registration_providers')),
            re_path(r'^account/', include('admin.common_auth.urls', namespace='auth')),
            re_path(r'^nodes/', include('admin.nodes.urls', namespace='nodes')),
            re_path(r'^preprints/', include('admin.preprints.urls', namespace='preprints')),
            re_path(r'^subjects/', include('admin.subjects.urls', namespace='subjects')),
            re_path(r'^users/', include('admin.users.urls', namespace='users')),
            re_path(r'^user-emails/', include('admin.user_emails.urls', namespace='user-emails')),
            re_path(r'^maintenance/', include('admin.maintenance.urls', namespace='maintenance')),
            re_path(r'^meetings/', include('admin.meetings.urls',
                                       namespace='meetings')),
            re_path(r'^metrics/', include('admin.metrics.urls',
                                      namespace='metrics')),
            re_path(r'^desk/', include('admin.desk.urls',
                                   namespace='desk')),
            re_path(r'^osf_groups/', include('admin.osf_groups.urls', namespace='osf_groups')),
            re_path(r'^management/', include('admin.management.urls', namespace='management')),
            re_path(r'^announcement/', include('admin.rdm_announcement.urls', namespace='announcement')),
            re_path(r'^addons/', include('admin.rdm_addons.urls', namespace='addons')),
            re_path(r'^oauth/', include('admin.rdm_addons.oauth.urls', namespace='oauth')),
            re_path(r'^statistics/', include('admin.rdm_statistics.urls', namespace='statistics')),
            re_path(r'^timestampadd/', include('admin.rdm_timestampadd.urls', namespace='timestampadd')),
            re_path(r'^keymanagement/', include('admin.rdm_keymanagement.urls', namespace='keymanagement')),
            re_path(r'^timestampsettings/', include('admin.rdm_timestampsettings.urls', namespace='timestampsettings')),
            re_path(r'^custom_storage_location/', include('admin.rdm_custom_storage_location.urls', namespace='custom_storage_location')),
            re_path(r'^institutional_storage_quota_control/', include('admin.institutional_storage_quota_control.urls',
                                                                  namespace='institutional_storage_quota_control')),
            re_path(r'^metadata/', include('admin.rdm_metadata.urls', namespace='metadata')),
            re_path(r'^user_identification_information/',
                include('admin.user_identification_information.urls', namespace='user_identification_information')),
            re_path(r'^user_identification_information_admin/',
                include('admin.user_identification_information_admin.urls', namespace='user_identification_information_admin')),
            re_path(r'^project_limit_number/', include('admin.project_limit_number.urls', namespace='project_limit_number')),
            re_path(r'^rdm_workflow/', include('admin.rdm_workflow.urls', namespace='rdm_workflow')),
        ]),
    ),
]

if DEBUG:
    import debug_toolbar

    urlpatterns += [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ]

admin.site.site_header = 'OSF-Admin administration'
