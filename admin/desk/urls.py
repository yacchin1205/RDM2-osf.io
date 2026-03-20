from django.urls import re_path

from admin.desk import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^customer/(?P<user_id>[a-z0-9]+)/$', views.DeskCustomer.as_view(),
        name='customer'),
    re_path(r'^cases/(?P<user_id>[a-z0-9]+)/$', views.DeskCaseList.as_view(),
        name='user_cases'),
]
