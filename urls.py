# coding=utf-8
from django.conf.urls import url

urlpatterns = [
    url(r'^$', 'esupa.views.view_subscribe', name='esupa-subscribe'),
    url(r'^verify$', 'esupa.views.view_verify', name='esupa-verify'),
    url(r'^doc/(.+)$', 'esupa.views.view_transaction_document', name='esupa-trans-doc'),
    url(r'^cron/(.+)$', 'esupa.views.view_cron', name='esupa-cron'),
    url(r'^processor/(.+)', 'esupa.views.view_processor', name='esupa-processor'),
    url(r'^(.*)$', 'esupa.views.view_subscribe', name='esupa-subscribe'),
]
