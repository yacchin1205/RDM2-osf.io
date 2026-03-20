from django.urls import re_path

from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.SpamList.as_view(), name='spam'),
    re_path(
        r'^(?P<spam_id>[a-z0-9]+)/$',
        views.SpamDetail.as_view(),
        name='detail'
    ),
    re_path(
        r'^(?P<spam_id>[a-z0-9]+)/email/$',
        views.EmailView.as_view(),
        name='email'
    ),
    re_path(
        r'^user/(?P<user_id>[a-z0-9]+)/$',
        views.UserSpamList.as_view(),
        name='user_spam'
    ),
]
