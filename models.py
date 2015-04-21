# coding=utf-8
from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now

PriceField = lambda: models.DecimalField(max_digits=7, decimal_places=2)


class EnumField(models.SmallIntegerField):
    # SmallIntegerField: "Values from -32768 to 32767 are safe in all databases supported by Django."
    def __init__(self, *args, **kwargs):
        if 'choices' not in kwargs:
            kwargs['choices'] = type(self).choices
        models.SmallIntegerField.__init__(self, *args, **kwargs)

    @classmethod
    def get(cls, value):
        for (key, desc) in cls.echoices:
            if key == value:
                return desc


class PmtMethods(EnumField):
    CASH = 0
    DEPOSIT = 1
    PROCESSOR = 2
    echoices = (
        (CASH, 'Em Mãos'),
        (DEPOSIT, 'Depósito Bancário'),
        (PROCESSOR, 'PagSeguro'),
    )


class SubsState(EnumField):
    NEW = 0
    ACCEPTABLE = 11
    WAITING = 33
    VERIFYING = 66
    UNPAID_STAFF = 88
    CONFIRMED = 99
    echoices = (
        (NEW, 'Nova'),
        (ACCEPTABLE, 'Preenchida'),
        (WAITING, 'Aguardando pagamento'),
        (VERIFYING, 'Verificando pagamento'),
        (UNPAID_STAFF, 'Tripulante não pago'),
        (CONFIRMED, 'Confirmada'),
    )


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

    def __str__(self):
        return self.name

    def current_subscription_stats(self):
        sfilter = self.subscription_set.filter
        add_count = lambda tu: tu + (sfilter(state=tu[0]).count(),)
        return map(add_count, Subscription.STATES)


class Optional(models.Model):
    event = models.ForeignKey(Event)
    name = models.CharField(max_length=20)
    price = PriceField()

    def __str__(self):
        return self.name


class QueueContainer(models.Model):
    event = models.OneToOneField(Event, primary_key=True)
    data = models.TextField()  # only because we're using json


class Subscription(models.Model):
    event = models.ForeignKey(Event)
    user = models.ForeignKey(User, null=True)
    created_at = models.DateTimeField(default=now, blank=True)
    state = SubsState(default=SubsState.NEW)
    wait_until = models.DateTimeField(null=True, blank=True)
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
    optionals = models.ManyToManyField(Optional, through='Opted')
    agreed = models.BooleanField(default=False)
    position = models.IntegerField(null=True, blank=True)
    paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.badge


class Opted(models.Model):
    optional = models.ForeignKey(Optional)
    subscription = models.ForeignKey(Subscription)
    paid = models.BooleanField(default=False)


class Transaction(models.Model):
    subscription = models.ForeignKey(Subscription)
    payee = models.CharField(max_length=10)
    value = PriceField()
    created_at = models.DateTimeField(default=now, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    accepted = models.BooleanField(default=False)
    verifier = models.ForeignKey(User, null=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    method = PmtMethods(default=PmtMethods.CASH)
    document = models.BinaryField()
    notes = models.TextField()
