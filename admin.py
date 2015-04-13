from django.contrib import admin
from . import models

class OptionalInline(admin.TabularInline):
	model = models.Optional
	extra = 0

class EventAdmin(admin.ModelAdmin):
	inlines = [OptionalInline]

admin.site.register(models.Event, EventAdmin)

class OptedInline(admin.TabularInline):
	model = models.Opted
	extra = 0

class TransactionInline(admin.TabularInline):
	model = models.Transaction
	extra = 0

class SubscriptionAdmin(admin.ModelAdmin):
	inlines = [OptedInline, TransactionInline]

admin.site.register(models.Subscription, SubscriptionAdmin)

