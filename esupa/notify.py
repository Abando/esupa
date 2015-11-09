# -*- coding: utf-8 -*-
#
# Copyright 2015, Ekevoo.com.
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
from logging import getLogger
from random import randint
from threading import Thread

from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext

from .models import Event, Subscription

log = getLogger(__name__)


def _mail(recipients, subject, body):
    it = 'mail#%d' % randint(0, 0x10000)

    def mail():
        try:
            log.info("Trying to send %s to %s about %s", it, ','.join(recipients), subject)
            EmailMessage(subject, ''.join(body), to=recipients).send(fail_silently=True)
            log.info("Sent %s alright", it)
        except ConnectionRefusedError:
            log.error("Connection failed for %s to %s", it, ','.join(recipients), exc_info=True)

    Thread(target=mail, name=it).start()  # this will come back to bite our butt, rest assured.


class EventNotifier:
    """ Sends e-mails to event staffers. """

    def __init__(self, event: Event):
        self.e = event

    def _send(self, subject, *body):
        subject = '[%s] %s' % (self.e.name, subject)
        recipients = User.objects.filter(is_staff=True).values_list('email', flat=True)
        _mail(recipients, subject, body)

    def must_check_subscription(self, subscription: Subscription, build_absolute_uri):
        from .views import TransactionList, SubscriptionList
        assert subscription.event == self.e
        subject = 'Check: %s' % subscription.badge
        body = (
            'Check subscription #%d (%s):' % (subscription.id, subscription.badge),
            build_absolute_uri(reverse(TransactionList.name, args=[subscription.id])),
            '',
            'All in %s:' % self.e.name,
            build_absolute_uri(reverse(SubscriptionList.name, args=[self.e.slug])))
        self._send(subject, *body)

    def sales_closed(self):
        self._send('Sales closed!', 'Sales closed for event #%d (%s)' % (self.e.id, self.e.name))


class Notifier:
    """ Sends e-mails to subscribers. """

    def __init__(self, subscription: Subscription):
        self.s = subscription

    def _send(self, subject, *body):
        event = self.s.event
        subject = '%s - %s' % (subject, event.name)
        body = (self.s.badge + ',', '') + body + ('', '=' * len(event.name), event.name)
        _mail([self.s.email], subject, body)

    def can_pay(self):
        """This can happen in two cases, (1) esupa staff data verify accepted, or (2) the queue moved."""
        self._send(ugettext("Payment Available"),
                   ugettext("Your subscription may be paid now. After payment is confirmed, the spot is yours."))

    def expired(self):
        """This means we've waited too long and the subscription can no longer be paid."""
        hours = self.s.event.payment_wait_hours
        self._send(ugettext("Payment Expired"),
                   ugettext("Your %d hour deadline was missed and you've been moved off the payment queue.") % hours)

    def data_denied(self):
        """Esupa staff data verify failed."""
        self._send(ugettext("Subscription Denied"),
                   ugettext("Your data has been verified and your subscription has been denied."))

    def confirmed(self):
        """Pay has been accepted."""
        self._send(ugettext("Subscription Confirmed"),
                   ugettext("Welcome! Your subscription is confirmed. :)"))

    def pay_denied(self):
        """Pay has been denied by the processor."""
        self._send(ugettext("Payment Cancelled"),
                   ugettext("The payment processor has cancelled your payment."))


class BatchNotifier:
    def __init__(self):
        self._expired = []
        self._can_pay = []
        self.expired = self._expired.append
        self.can_pay = self._can_pay.append

    def send_notifications(self):
        for subscription in self._expired:
            Notifier(subscription).expired()
        for subscription in self._can_pay:
            Notifier(subscription).can_pay()
