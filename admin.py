from django.contrib import admin

from inev import models

class OpcionalInline(admin.TabularInline):
	model = models.Opcional
	extra = 0

class EventoAdmin(admin.ModelAdmin):
	inlines = [OpcionalInline]

admin.site.register(models.Evento, EventoAdmin)

class OptadoInline(admin.TabularInline):
	model = models.Optado
	extra = 0

class TransacaoInline(admin.TabularInline):
	model = models.Transacao
	extra = 0

class InscricaoAdmin(admin.ModelAdmin):
	inlines = [OptadoInline, TransacaoInline]

admin.site.register(models.Inscricao, InscricaoAdmin)

