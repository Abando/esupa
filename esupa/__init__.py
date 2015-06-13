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
from django.apps import AppConfig


class EsupaApp(AppConfig):
    name = __name__
    verbose_name = 'Event Subscription and Payment'

    def ready(self):
        from .payment import load_submodules

        load_submodules()


default_app_config = '.'.join((__name__, EsupaApp.__name__))
