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
from datetime import date, timedelta
from decimal import Decimal
from logging import getLogger

from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now

log = getLogger(__name__)
PriceField = lambda: models.DecimalField(max_digits=7, decimal_places=2)
payment_names = {}  # Will be filled by payment/__init__.py


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

    def __init__(self, value=None):
        for row in type(self).choices:
            if value is None or value in row:
                self._value = row[0]
                self._descr = row[1]
                return
        raise ValueError()

    def __str__(self):
        return self._descr

    def __repr__(self):
        return '%s(%d)' % (str(type(self)), self._value)


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
    agreement_url = models.URLField(blank=True)
    starts_at = models.DateTimeField()
    min_age = models.IntegerField(default=0)
    price = PriceField()
    capacity = models.IntegerField()
    subs_open = models.BooleanField(default=False)
    subs_toggle = models.DateTimeField(null=True, blank=True)
    sales_open = models.BooleanField(default=False)
    sales_toggle = models.DateTimeField(null=True, blank=True)
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
            return now().date()

    def cron(self, present):
        if self.subs_toggle and self.subs_toggle < present:
            self.subs_toggle = None
            self.subs_open = not self.subs_open
        if self.sales_toggle and self.sales_toggle < present:
            self.sales_toggle = None
            self.sales_open = not self.sales_open


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
    phone = models.CharField(max_length=20)
    born = models.DateField()
    shirt_size = models.CharField(max_length=4)
    blood = models.CharField(max_length=3)
    health_insured = models.BooleanField(default=False)
    contact = models.TextField(blank=True)
    medication = models.TextField(blank=True)
    optionals = models.ManyToManyField(Optional, blank=True)
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
        return False if self.wait_until is None else self.wait_until < now()

    @waiting.setter
    def waiting(self, value):
        if not value:
            self.wait_until = None
        elif not self.waiting:  # only reset wait time if it's not running.
            self.wait_until = now() + timedelta(hours=self.event.payment_wait_hours)

    @property
    def price(self) -> Decimal:
        return self.event.price + (self.optionals.aggregate(models.Sum('price'))['price__sum'] or 0)

    @property
    def str_state(self) -> str:
        return str(SubsState(self.state))


class Transaction(models.Model):
    subscription = models.ForeignKey(Subscription)
    payee = models.CharField(max_length=10, blank=True)
    value = PriceField()
    created_at = models.DateTimeField(auto_now=True)
    method = models.SmallIntegerField(default=0)
    remote_identifier = models.CharField(max_length=50, blank=True)
    mimetype = models.CharField(max_length=255, blank=True)
    document = models.BinaryField(null=True)
    filled_at = models.DateTimeField(null=True, blank=True)
    verifier = models.ForeignKey(User, blank=True, null=True)
    accepted = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def end(self, sucessfully) -> bool:
        """
        Closes a transaction, and will propagate the appropriate changes to the belonging subscription.

        :return bool: Whether the state of the subscription was changed.
        """
        self.accepted = sucessfully
        if not self.ended_at:
            self.ended_at = now()
        self.save()
        subscription = self.subscription
        if subscription.state >= SubsState.CONFIRMED:
            # A confirmed subscription can't be touched.
            return False
        elif sucessfully:
            # Transaction was accepted.
            subscription.raise_state(SubsState.CONFIRMED)
            subscription.save()
            return True
        elif subscription.transaction_set.filter(ended_at__isnull=True, method=self.method).exists():
            # Pending transaction of this type was rejected, wasn't the last one.
            return False
        else:
            # Last pending transaction of this type was rejected.
            subscription.state = SubsState.ACCEPTABLE
            subscription.position = None
            subscription.waiting = False
            subscription.save()
            return True

    @property
    def str_method(self):
        return payment_names.get(self.method)
