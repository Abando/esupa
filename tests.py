# coding=utf-8
from datetime import date, timedelta
from logging import getLogger

from django.test import TestCase
from django.utils.timezone import now

from .models import Event, Optional

logger = getLogger(__name__)


class BasicModelVerification(TestCase):
    def setUp(self):
        self.now = now()

        self.e1 = Event.objects.create(name="Summer Sun Celebration",
                                       starts_at=date(2010, 10, 10),
                                       capacity=200, price=0)
        self.o1 = Optional.objects.create(event=self.e1, name="Front Row Seat", price=3000)

        self.e2 = Event.objects.create(name="EQG Magic Mirror Opens",
                                       starts_at=self.now + timedelta(weeks=117),
                                       subs_open=True, sales_open=True,
                                       capacity=1, price=10)
        self.o2 = Optional.objects.create(event=self.e2, name="Talking Dog", price=5)

        self.e3 = Event.objects.create(name="Princess Sweetie Belle Coronation",
                                       starts_at=self.now + timedelta(weeks=500),
                                       subs_open=True,
                                       capacity=200, price=2000)

        # I should've started this way sooner. It's too late now... :(
