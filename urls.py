# coding=utf-8
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.view_subscribe, name='esupa-subscribe'),
    url(r'^verify$', views.view_verify, name='esupa-verify'),
    url(r'^verify/(.+)$', views.view_verify_event, name='esupa-verify-event'),
    url(r'^doc/(.+)$', views.view_transaction_document, name='esupa-trans-doc'),
    url(r'^cron/(.+)$', views.view_cron, name='esupa-cron'),
    url(r'^processor/(.+)', views.view_processor, name='esupa-processor'),
    url(r'^(.*)$', views.view_subscribe, name='esupa-subscribe'),
]
