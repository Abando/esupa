from django.contrib.auth.models import User
from django.db import models

PriceField = lambda:models.DecimalField(max_digits=7, decimal_places=2)

class Event(models.Model):
	name = models.CharField(max_length=20)
	starts_at = models.DateTimeField()
	min_age = models.IntegerField(default=0)
	price = PriceField()
	capacity = models.IntegerField()
	subs_open = models.BooleanField(default=False)
	subs_start_at = models.DateTimeField(null=True, blank=True)
	sales_open = models.BooleanField(default=False)
	sales_start_at = models.DateTimeField(null=True, blank=True)
	def __str__(self): return self.name

class Optional(models.Model):
	event = models.ForeignKey(Event)
	name = models.CharField(max_length=20)
	price = PriceField()
	capacity = models.IntegerField(null=True, blank=True)
	def __str__(self): return self.name

class Subscription(models.Model):
	event = models.ForeignKey(Event)
	user = models.ForeignKey(User, null=True)
	created_at = models.DateTimeField()
	full_name = models.CharField(max_length=80)
	document = models.CharField(max_length=30)
	badge = models.CharField(max_length=30)
	email = models.CharField(max_length=80)
	area = models.CharField(max_length=2)
	phone = models.CharField(max_length=9)
	born = models.DateField()
	shirt_size = models.CharField(max_length=4)
	blood = models.CharField(max_length=3)
	health_insured = models.BooleanField(default=False)
	contact = models.TextField()
	medication = models.TextField()
	agreed = models.BooleanField(default=False)
	position = models.IntegerField(null=True, blank=True)
	paid = models.BooleanField(default=False)
	paid_at = models.DateTimeField(null=True, blank=True)
	def __str__(self): return self.badge

class Opted(models.Model):
	optional = models.ForeignKey(Optional)
	subscription = models.ForeignKey(Subscription)
	paid = models.BooleanField(default=False)

class Transaction(models.Model):
	DEPOSIT = 'D'
	PAGSEGURO = 'P'
	CASH = 'C'
	METHODS = (
		(DEPOSIT, 'Depósito Bancário'),
		(PAGSEGURO, 'PagSeguro'),
		(CASH, 'Em Mãos'),
	)
	subscription = models.ForeignKey(Subscription)
	payee = models.CharField(max_length=10)
	started_at = models.DateTimeField()
	ended_at = models.DateTimeField(null=True, blank=True)
	accepted = models.BooleanField(default=False)
	value = PriceField()
	method = models.CharField(max_length=1, choices=METHODS, default=CASH)
	document = models.CharField(max_length=50)
	notes = models.TextField()

