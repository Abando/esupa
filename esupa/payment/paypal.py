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

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.http import HttpRequest
from paypalrestsdk import configure, Payment  # sudo -H pip3 install paypalrestsdk

from .base import PaymentBase
from ..notify import Notifier
from ..queue import QueueAgent
from ..utils import FunctionDictionary, prg_redirect

log = getLogger(__name__)


def _find_href(links, rel):
    for link in links:
        if link.rel == rel:
            return link.href
    raise KeyError


class PaymentMethod(PaymentBase):
    CODE = 3
    TITLE = 'PayPal'
    CONFIGURATION_KEYS = ('PAYPAL',)

    @classmethod
    def static_init(cls):
        super().static_init()
        configure(settings.PAYPAL)

    def start_payment(self, request, amount):
        event = self.subscription.event
        self.transaction.amount = amount
        payment = Payment({
            'transactions': [{'amount': {'total': amount.to_eng_string(),
                                         'currency': 'BRL'},
                              'description': event.name}],
            'payer': {'payment_method': 'paypal'},
            'redirect_urls': {'return_url': self.my_pay_url(request),
                              'cancel_url': self.my_view_url(request)},
            'intent': 'sale'})
        if payment.create():
            self.transaction.remote_identifier = payment.id
            self.transaction.save()
            return prg_redirect(_find_href(payment.links, 'approval_url'))
        else:
            log.error('Data returned error. %s', repr(payment))
            raise ValueError('PayPal denied pay. %s' % repr(payment))

    @classmethod
    def class_view(cls, request: HttpRequest):
        payment_id = request.GET.get('paymentId')
        payer_id = request.GET.get('PayerID')
        if not payment_id:
            raise SuspiciousOperation
        payment = PaymentMethod(payment_id)
        paypal = Payment.find(payment_id)
        if not paypal.execute({'payer_id': payer_id}):
            raise ValueError('PayPal did not complete pmt %s' % payment_id)
        payment.callback_view(paypal)
        # This is actually the user here, not a callback bot! So we must return to base.
        # TODO: What if the user never returns home after paying? Should we poll pending transactions?
        return prg_redirect(payment.my_view_url(request))

    def callback_view(self, data: dict):
        try:
            self.transaction.notes += '\n[%s] %s %s' % (data['update_time'], data['id'], data['state'])
            queue = QueueAgent(self.subscription)
            notify = Notifier(self.subscription)
            state = data['state']
            self.state_callback.get(state)(self, state=state, queue=queue, notify=notify)
        finally:
            # No rollbacks please!
            self.transaction.save()
            self.subscription.save()

    @FunctionDictionary
    def state_callback(self, state: str, **_):
        log.debug("PayPal unknown state <%s>, transaction #%d: %s",
                  state, self.transaction.id, self.transaction.remote_identifier)

    @state_callback.register('approved')
    def state_callback(self, queue: QueueAgent, notify: Notifier, **_):
        if self.transaction.end(sucessfully=True):
            self.subscription.position = queue.add()
            notify.confirmed()

    @state_callback.register('canceled', 'expired', 'failed')
    def state_callback(self, queue: QueueAgent, notify: Notifier, **_):
        if self.transaction.end(sucessfully=False):
            queue.remove()
            notify.pay_denied()
