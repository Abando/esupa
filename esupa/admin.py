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
from django.contrib import admin

from . import models


def tabular_inlines_of(*children_types):
    def one_inline(target):
        class MyInline(admin.TabularInline):
            model = target
            extra = 0

        return MyInline

    return tuple(map(one_inline, children_types))


class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'starts_at', 'subs_open', 'sales_open')
    list_display_links = ('name',)
    list_filter = ('subs_open', 'sales_open')
    inlines = tabular_inlines_of(models.Optional)
    ordering = ('starts_at',)


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('event', 'badge', 'state', 'waiting', 'email', 'user', 'age_at_event')
    list_display_links = ('badge',)
    list_filter = ('event', 'state')
    inlines = tabular_inlines_of(models.Transaction)
    ordering = ('-id',)


admin.site.register(models.Event, EventAdmin)
admin.site.register(models.Subscription, SubscriptionAdmin)
