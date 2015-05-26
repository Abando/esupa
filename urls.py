# coding=utf-8
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.subscribe, name='esupa-subscribe'),
    url(r'^verify$', views.verify, name='esupa-verify'),
    url(r'^verify/(.+)$', views.verify_event, name='esupa-verify-event'),
    url(r'^doc/(.+)$', views.transaction_document, name='esupa-trans-doc'),
    url(r'^cron/(.+)$', views.cron, name='esupa-cron'),
    url(r'^processor/(.+)', views.processor, name='esupa-processor'),
    url(r'^(.*)$', views.subscribe, name='esupa-subscribe'),
]
