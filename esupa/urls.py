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
from django.conf import urls

from . import views


def url(regex, view, kwargs=None, name=None, prefix=''):
    if not name and hasattr(view, 'name'):
        name = view.name
    return urls.url(regex, view, kwargs, name, prefix)


urlpatterns = [
    url(r'^view$', views.view),
    url(r'^view/(.*)$', views.view),
    url(r'^edit$', views.edit),
    url(r'^edit/(.*)$', views.edit),
    url(r'^pay/(.*)$', views.paying),
    url(r'^doc/(.+)$', views.transaction_document),
    url(r'^cron/(.+)$', views.cron_view),
    url(r'^check$', views.EventList.as_view()),
    url(r'^check/e/(\d+)$', views.SubscriptionList.as_view()),
    url(r'^check/d/(\d+)$', views.TransactionList.as_view()),
    url(r'^(.*)$', views.view),
]
