from django.urls import re_path

from api.mapcore import views

app_name = 'osf'

urlpatterns = [
    # Examples:
    # re_path(r'^$', 'api.views.home', name='home'),
    # re_path(r'^blog/', include('blog.urls')),
    re_path(r'^groups/$', views.MapCoreGroupList.as_view(), name=views.MapCoreGroupList.view_name),
]
