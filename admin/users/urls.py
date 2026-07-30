from django.urls import re_path

from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.UserFormView.as_view(), name='search'),
    re_path(r'^flagged_spam$', views.UserFlaggedSpamList.as_view(), name='flagged-spam'),
    re_path(r'^known_spam$', views.UserKnownSpamList.as_view(), name='known-spam'),
    re_path(r'^known_ham$', views.UserKnownHamList.as_view(), name='known-ham'),
    re_path(r'^workshop$', views.UserWorkshopFormView.as_view(), name='workshop'),
    re_path(r'^(?P<guid>[a-z0-9]+)/$', views.UserView.as_view(), name='user'),
    re_path(r'^search/(?P<name>.*)/$', views.UserSearchList.as_view(), name='search_list'),
    re_path(r'^(?P<guid>[a-z0-9]+)/reset-password/$', views.ResetPasswordView.as_view(), name='reset_password'),
    re_path(r'^(?P<guid>[a-z0-9]+)/gdpr_delete/$', views.UserGDPRDeleteView.as_view(), name='GDPR_delete'),
    re_path(r'^(?P<guid>[a-z0-9]+)/disable/$', views.UserDeleteView.as_view(), name='disable'),
    re_path(r'^(?P<guid>[a-z0-9]+)/disable_spam/$', views.SpamUserDeleteView.as_view(), name='spam_disable'),
    re_path(r'^(?P<guid>[a-z0-9]+)/enable_ham/$', views.HamUserRestoreView.as_view(), name='ham_enable'),
    re_path(r'^(?P<guid>[a-z0-9]+)/reactivate/$', views.UserDeleteView.as_view(), name='reactivate'),
    re_path(r'^(?P<guid>[a-z0-9]+)/get_claim_urls/$', views.GetUserClaimLinks.as_view(), name='get_claim_urls'),
    re_path(r'^(?P<guid>[a-z0-9]+)/two-factor/disable/$', views.User2FactorDeleteView.as_view(), name='remove2factor'),
    re_path(r'^(?P<guid>[a-z0-9]+)/system_tags/add/$', views.UserAddSystemTag.as_view(), name='add_system_tag'),
    re_path(r'^(?P<guid>[a-z0-9]+)/get_confirmation/$', views.GetUserConfirmationLink.as_view(), name='get_confirmation'),
    re_path(r'^(?P<guid>[a-z0-9]+)/get_reset_password/$', views.GetPasswordResetLink.as_view(), name='get_reset_password'),
    re_path(r'^(?P<guid>[a-z0-9]+)/reindex_elastic_user/$', views.UserReindexElastic.as_view(), name='reindex-elastic-user'),
    re_path(r'^(?P<guid>[a-z0-9]+)/merge_accounts/$', views.UserMergeAccounts.as_view(), name='merge-accounts'),
    re_path(r'^(?P<guid>[a-z0-9]+)/quota/$', views.UserQuotaView.as_view(), name='quota'),
    re_path(r'^(?P<guid>[a-z0-9]+)/details/$', views.UserDetailsView.as_view(), name='user_details'),
    re_path(r'^(?P<guid>[a-z0-9]+)/institution_quota/$', views.UserInstitutionQuotaView.as_view(), name='institution_quota'),
]
