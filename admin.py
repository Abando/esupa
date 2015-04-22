# coding=utf-8
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
register_with_tabular_inlines(Subscription, Opted, Transaction)
