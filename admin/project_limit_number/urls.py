from django.urls import include, re_path

app_name = 'admin'

urlpatterns = [
    re_path(r'^settings/', include('admin.project_limit_number.setting.urls', namespace='settings')),
    re_path(r'^templates/', include('admin.project_limit_number.template.urls', namespace='templates')),
]
