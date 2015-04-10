# -*- encoding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User

PrecoField = lambda:models.DecimalField(max_digits=7, decimal_places=2)

class Evento(models.Model):
	nome = models.CharField(max_length=20)
	quandoAcontece = models.DateTimeField()
	idadeMinima = models.IntegerField(default=0)
	preco = PrecoField()
	inscricoesAbertas = models.BooleanField(default=False)
	inscricoesQuandoAbrir = models.DateTimeField(null=True)
	vendasAbertas = models.BooleanField(default=False)
	vendasQuandoAbrir = models.DateTimeField(null=True)
	def __str__(self): return self.nome

class Opcional(models.Model):
	evento = models.ForeignKey(Evento)
	nome = models.CharField(max_length=20)
	preco = PrecoField()
	vagasLimitadas = models.BooleanField(default=False)
	def __str__(self): return self.nome

class Inscricao(models.Model):
	evento = models.ForeignKey(Evento)
	user = models.ForeignKey(User, null=True)
	cracha = models.CharField(max_length=30)
	quandoCriou = models.DateTimeField()
	posicao = models.IntegerField(null=True)
	quitado = models.BooleanField(default=False)
	quandoQuitou = models.DateTimeField(null=True)
	def __str__(self): return self.cracha

class Optado(models.Model):
	opcional = models.ForeignKey(Opcional)
	inscricao = models.ForeignKey(Inscricao)
	quitado = models.BooleanField(default=False)

class Transacao(models.Model):
	DEPOSITO = 'D'
	PAGSEGURO = 'P'
	EM_MAOS = 'M'
	FORMAS_DE_PAGAMENTO = (
		(DEPOSITO, 'Depósito Bancário'),
		(PAGSEGURO, 'PagSeguro'),
		(EM_MAOS, 'Em Mãos'),
	)
	inscricao = models.ForeignKey(Inscricao)
	recipiente = models.CharField(max_length=10)
	iniciada = models.DateTimeField()
	encerrada = models.DateTimeField(null=True)
	completada = models.BooleanField(default=False)
	valor = PrecoField()
	formaDePagamento = models.CharField(
		max_length=1, choices=FORMAS_DE_PAGAMENTO, default=EM_MAOS)
	codigoDocumento = models.CharField(max_length=50)
	anotacoes = models.TextField()
