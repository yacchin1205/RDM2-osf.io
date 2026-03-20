from __future__ import absolute_import

from django.urls import re_path
from django.urls import reverse_lazy
from django.contrib.auth.views import password_change, password_change_done

from admin.common_auth import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^shib-login/?$', views.ShibLoginView.as_view(), name='shib-login'),
    re_path(r'^login/?$', views.LoginView.as_view(), name='login'),
    re_path(r'^logout/$', views.logout_user, name='logout'),
    re_path(r'^register/$', views.RegisterUser.as_view(), name='register'),
    re_path(r'^password_change/$', password_change,
        {'post_change_redirect': reverse_lazy('auth:password_change_done')},
        name='password_change'),
    re_path(r'^password_change/done/$', password_change_done,
        {'template_name': 'password_change_done.html'},
        name='password_change_done'),
    re_path(r'^settings/desk/$', views.DeskUserCreateFormView.as_view(), name='desk'),
    re_path(r'^settings/desk/update/$', views.DeskUserUpdateFormView.as_view(), name='desk_update'),
]
