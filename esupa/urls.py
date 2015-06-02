# coding=utf-8
#
# Copyright 2015, Abando.com.br
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.
#
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^view$', views.view, name='esupa-view'),
    url(r'^view/(.*)$', views.view, name='esupa-view'),
    url(r'^edit$', views.edit, name='esupa-edit'),
    url(r'^edit/(.*)$', views.edit, name='esupa-edit'),
    url(r'^pay$', views.pay, name='esupa-pay'),
    url(r'^pay/(.*)$', views.pay, name='esupa-pay'),
    url(r'^paying/(.+)', views.paying, name='esupa-paying'),
    url(r'^verify$', views.verify, name='esupa-verify'),
    url(r'^verify/(.+)$', views.verify_event, name='esupa-verify-event'),
    url(r'^doc/(.+)$', views.transaction_document, name='esupa-trans-doc'),
    url(r'^cron/(.+)$', views.cron_view, name='esupa-cron'),
    url(r'^(.*)$', views.view, name='esupa-subscribe'),
]
