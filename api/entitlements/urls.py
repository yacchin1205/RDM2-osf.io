from django.urls import re_path

from api.entitlements import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^login_availability/$', views.LoginAvailability.as_view(), name=views.LoginAvailability.view_name),
]
