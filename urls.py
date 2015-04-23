# coding=utf-8
from django.conf.urls import url

urlpatterns = [
    url(r'^$', 'esupa.views.index', name='esupa-index'),
    url(r'^doc(\d+)$', 'esupa.views.view_transaction_document', name='esupa-trans-doc'),
    url(r'^manage$', 'esupa.views.manage', name='esupa-manage'),
    url(r'^pagseguro$', 'esupa.payment.callback_pagseguro', name='esupa-callback-pagseguro')
]
