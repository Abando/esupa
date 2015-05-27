# coding=utf-8
#
# Copyright 2015, Abando.
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
from django.contrib import admin

from .models import *


def register_with_tabular_inlines(my_type, *children_types):
    def one_inline(target):
        class MyInline(admin.TabularInline):
            model = target
            extra = 0

        return MyInline

    class MyAdmin(admin.ModelAdmin):
        inlines = tuple(map(one_inline, children_types))

    admin.site.register(my_type, MyAdmin)


register_with_tabular_inlines(Event, Optional)
register_with_tabular_inlines(Subscription, Transaction)
