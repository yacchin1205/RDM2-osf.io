from django.urls import re_path
from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.InstitutionListViewStat.as_view(), name='institutions'),
    re_path(r'^(?P<institution_id>-?[0-9]+)/$', views.StatisticsView.as_view(), name='statistics'),
    re_path(r'^index$', views.IndexView.as_view(), name='index'),
    re_path(r'^(?P<institution_id>-?[0-9]+)/graph/(?P<graph_type>\w+)_(?P<provider>\w+)\.(\w+)$',
        views.ImageView.as_view(), name='graph'),
    re_path(r'^gather/(?P<access_token>-?\w+)/$', views.GatherView.as_view(), name='gather'),
    re_path(r'^report/(?P<institution_id>-?[0-9]+)/$', views.create_pdf, name='report'),
    re_path(r'^csv/(?P<institution_id>-?[0-9]+)/$', views.create_csv, name='csv'),
    re_path(r'^mail/(?P<institution_id>-?[0-9]+)/$', views.SendView.as_view(), name='mail'),
    re_path(r'^test/mail/$', views.send_stat_mail, name='test'),
]
