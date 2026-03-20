from django.urls import re_path
from . import views

app_name = 'admin'

urlpatterns = [
    # re_path(r'^$', views.InstitutionEntitlementList.as_view(), name='list'),
    re_path(r'^bulk_add/$', views.BulkAddInstitutionEntitlement.as_view(), name='bulk_add'),
    # re_path(r'^(?P<entitlement_id>[0-9]+)/toggle/$', views.ToggleInstitutionEntitlement.as_view(http_method_names=['post']), name='toggle'),
    # re_path(r'^(?P<entitlement_id>[0-9]+)/delete/$', views.DeleteInstitutionEntitlement.as_view(http_method_names=['post']), name='delete'),
]
