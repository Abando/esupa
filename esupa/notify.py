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

from .models import Event, Subscription, SubsState

log = getLogger(__name__)


def _mail(recipients, subject, body):
    it = 'mail#%d' % randint(0, 0x10000)

    def mail():
        try:
            log.info("Trying to send %s to %s about %s", it, ','.join(recipients), subject)
            EmailMessage(subject, '\n'.join(body), to=recipients).send(fail_silently=True)
            log.info("Sent %s alright", it)
        except ConnectionRefusedError:
            log.error("Connection failed for %s to %s", it, ','.join(recipients), exc_info=True)

    Thread(target=mail, name=it).start()  # this will come back to bite our butt, rest assured.


class EventNotifier:
    """ Sends e-mails to event staffers. """

    def __init__(self, event: Event):
        self.e = event

    def send(self, subject, *body):
        subject = '[%s] %s' % (self.e.name, subject)
        recipients = User.objects.filter(is_staff=True).values_list('email', flat=True)
        _mail(recipients, subject, body)

    def sales_closed(self):
        self.send('Sales closed!', 'Sales closed for event #%d (%s)' % (self.e.id, self.e.name))


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

    def saved(self, old_state, build_absolute_uri):
        from .views import view
        self._send(
            ugettext("Subscription Saved"),
            ugettext("Your changes were saved."),
            "",
            ugettext("Your subscription is now: %s") % self.s.str_state,
            "",
            ugettext("Should you need to make any further updates, go to:"),
            build_absolute_uri(reverse(view.name, args=[self.s.event.slug])))
        if old_state != self.s.state:
            new_state = self.s.state
            notification = "Changed from %d (%s) to %d (%s)" % (
                old_state, SubsState(old_state), new_state, SubsState(new_state))
            self.notify_staff(notification, build_absolute_uri)

    def notify_staff(self, notification: str, build_absolute_uri):
        from .views import TransactionList, SubscriptionList
        EventNotifier(self.s.event).send(
            "Check: %s" % self.s.badge,
            "Subscription #%d %s %s:" % (self.s.id, self.s.email, self.s.badge),
            notification,
            build_absolute_uri(reverse(TransactionList.name, args=[self.s.id])),
            "",
            "All in %s:" % self.s.event.name,
            build_absolute_uri(reverse(SubscriptionList.name, args=[self.s.event.slug])))


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

    def __repr__(self):
        if self._expired or self._can_pay:
            return "<BatchNotifier with %d, %d>" % (len(self._expired), len(self._can_pay))
        else:
            return "<BatchNotifier, empty>"
