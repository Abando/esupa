# coding=utf-8
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models


PriceField = lambda: models.DecimalField(max_digits=7, decimal_places=2)


class Enum:
    choices = ()

    @classmethod
    def field(cls, **kwargs):
        # SmallIntegerField: "Values from -32768 to 32767 are safe in all databases supported by Django."
        return models.SmallIntegerField(choices=cls.choices, **kwargs)

    @classmethod
    def get(cls, value):
        for (key, desc) in cls.choices:
            if key == value:
                return desc
            elif desc == value:
                return key

    def __init__(self, value):
        for row in type(self).choices:
            if value in row:
                self._value = row[0]
                self._descr = row[1]
                return
        raise ValueError()

    def __str__(self):
        return self._descr

    def __repr__(self):
        return '%s(%d)' % (str(type(self)), self._value)


class PmtMethod(Enum):
    CASH = 0
    DEPOSIT = 1
    PROCESSOR = 2
    choices = (
        (CASH, 'Em Mãos'),
        (DEPOSIT, 'Depósito Bancário'),
        (PROCESSOR, 'PagSeguro'),
    )


class SubsState(Enum):
    NEW = 0
    ACCEPTABLE = 11
    QUEUED_FOR_PAY = 33
    EXPECTING_PAY = 55
    VERIFYING_PAY = 66
    UNPAID_STAFF = 88
    CONFIRMED = 99
    VERIFYING_DATA = -1
    DENIED = -9
    choices = (
        (NEW, 'Nova'),
        (ACCEPTABLE, 'Preenchida'),
        (QUEUED_FOR_PAY, 'Em fila para poder pagar'),
        (EXPECTING_PAY, 'Aguardando pagamento'),
        (VERIFYING_PAY, 'Verificando pagamento'),
        (UNPAID_STAFF, 'Tripulante não pago'),
        (CONFIRMED, 'Confirmada'),
        (VERIFYING_DATA, 'Verificando dados'),
        (DENIED, 'Rejeitada'),
    )


class Event(models.Model):
    name = models.CharField(max_length=20)
    slug = models.SlugField(blank=True)
    starts_at = models.DateTimeField()
    min_age = models.IntegerField(default=0)
    price = PriceField()
    capacity = models.IntegerField()
    subs_open = models.BooleanField(default=False)
    subs_start_at = models.DateTimeField(null=True, blank=True)
    sales_open = models.BooleanField(default=False)
    sales_start_at = models.DateTimeField(null=True, blank=True)
    deposit_info = models.TextField(blank=True)
    payment_wait_hours = models.IntegerField(default=48)
    data_to_be_checked = models.TextField(blank=True)

    def __str__(self):
        return self.name

    def current_subscription_stats(self):
        sfilter = self.subscription_set.filter
        filtered_count = lambda tu: sfilter(state=tu[0]).count()
        return map(filtered_count, SubsState.choices)

    @property
    def num_confirmed(self):
        return self.subscription_set.filter(state__gte=SubsState.UNPAID_STAFF).count()

    @property
    def num_pending(self):
        return self.subscription_set.filter(state__lt=SubsState.UNPAID_STAFF, state__gt=SubsState.ACCEPTABLE).count()

    @property
    def num_openings(self):
        return self.capacity - self.subscription_set.filter(state__gt=SubsState.ACCEPTABLE).count()

    @property
    def max_born(self):
        if self.min_age:
            return date(self.starts_at.year - self.min_age, self.starts_at.month, self.starts_at.day)
        else:
            return date.today()


class Optional(models.Model):
    event = models.ForeignKey(Event)
    name = models.CharField(max_length=20)
    price = PriceField()

    def __str__(self):
        return self.name


class QueueContainer(models.Model):
    event = models.OneToOneField(Event, primary_key=True)
    data = models.TextField(default='[]')  # only because we're using json


class Subscription(models.Model):
    event = models.ForeignKey(Event)
    user = models.ForeignKey(User, null=True)
    created_at = models.DateTimeField(auto_now=True)
    state = SubsState.field(default=SubsState.NEW)
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
    contact = models.TextField(blank=True)
    medication = models.TextField(blank=True)
    optionals = models.ManyToManyField(Optional)
    agreed = models.BooleanField(default=False)
    position = models.IntegerField(null=True, blank=True)
    paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.badge

    def raise_state(self, state):
        if self.state < state:
            self.state = state

    @property
    def waiting(self) -> bool:
        return False if self.wait_until is None else self.wait_until < datetime.now()

    @waiting.setter
    def waiting(self, value):
        if not value:
            self.wait_until = None
        elif not self.waiting:  # only reset wait time if it's not running.
            self.wait_until = datetime.now() + timedelta(hours=self.event.payment_wait_hours)

    @property
    def price(self) -> Decimal:
        return self.event.price + (self.optionals.aggregate(models.Sum('price'))['price__sum'] or 0)


class Transaction(models.Model):
    subscription = models.ForeignKey(Subscription)
    payee = models.CharField(max_length=10)
    value = PriceField()
    created_at = models.DateTimeField(auto_now=True)
    method = PmtMethod.field(default=PmtMethod.CASH)
    remote_identifier = models.CharField(max_length=50, blank=True)
    document = models.BinaryField(null=True)
    filled_at = models.DateTimeField(null=True, blank=True)
    verifier = models.ForeignKey(User, null=True)
    accepted = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
