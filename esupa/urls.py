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

VIEW = 'esupa-view'
EDIT = 'esupa-edit'
PAY = 'esupa-pay'
VERIFY = 'esupa-verify'
VERIFY_EVENT = 'esupa-verify-event'
DOCUMENT = 'esupa-verify-event'
CRON = 'esupa-cron'

urlpatterns = [
    url(r'^view$', views.view, name=VIEW),
    url(r'^view/(.*)$', views.view, name=VIEW),
    url(r'^edit$', views.edit, name=EDIT),
    url(r'^edit/(.*)$', views.edit, name=EDIT),
    url(r'^pay/(.*)$', views.paying, name=PAY),
    url(r'^verify$', views.verify, name=VERIFY),
    url(r'^verify/(.+)$', views.verify_event, name=VERIFY_EVENT),
    url(r'^doc/(.+)$', views.transaction_document, name=DOCUMENT),
    url(r'^cron/(.+)$', views.cron_view, name=CRON),
    url(r'^(.*)$', views.view, name=VIEW),
]
