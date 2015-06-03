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
from logging import getLogger

# sudo -H pip3 install django-pagseguro2
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpRequest
from django.shortcuts import redirect
from pagseguro.api import PagSeguroApi, PagSeguroItem
from pagseguro.settings import TRANSACTION_STATUS

from . import PaymentBase
from .. import urls
from ..models import SubsState, Transaction
from ..notify import Notifier
from ..queue import QueueAgent

log = getLogger(__name__)


class Payment(PaymentBase):
    CODE = 2
    TITLE = 'PagSeguro'

    def __init__(self, data=None, **kwargs):
        PaymentBase.__init__(**kwargs)
        self.data = data

    def start_payment(self, amount):
        event = self.subscription.event
        api = PagSeguroApi()
        api.params['reference'] = self.transaction.id
        api.params['notificationURL'] = settings.BASE_PUBLIC_URI + reverse(urls.PAY, args=['pagseguro'])
        log.debug('Set notification URI: %s', api.params['notificationURL'])
        api.add_item(PagSeguroItem(id=self.transaction.id, description=event.name, amount=amount, quantity=1))
        data = api.checkout()
        if data['success']:
            return redirect(data['redirect_url'])
        else:
            log.error('Data returned error. %s', repr(data))
            raise ValueError('PagSeguro denied pay. %s' % repr(data))

    @classmethod
    def class_view(cls, request: HttpRequest):
        notification_code = request.POST.get('notificationCode', None)
        notification_type = request.POST.get('notificationType', None)
        if notification_code and notification_type == 'transaction':
            data = PagSeguroApi().get_notification(notification_code)
            tid = int(data['reference'])
            transaction = Transaction.objects.get(id=tid)
            payment = Payment(transaction=transaction)
            payment.callback_view(data)

    def callback_view(self, data: dict):
        try:
            self.transaction.remote_identifier = data['code']
            self.transaction.notes += '\n[%s] %s %s' % (data['lastEventDate'], data['code'], data['status'])
            queue = QueueAgent(self.subscription)
            notify = Notifier(self.subscription)
            status = TRANSACTION_STATUS[data['status']]
            self.status_callback[status](self, status=status, queue=queue, notify=notify)
        finally:
            # No rollbacks please!
            self.transaction.save()
            self.subscription.save()

    status_callback = CallbackDictionary()

    @status_callback.register('aguardando', 'em_analise')
    def status_callback(self, queue: QueueAgent, **_):
        # This bit of logic is not strictly needed. I'm just making sure data is still sane.
        # 'em_analise' means PagSeguro is verifying pay, not esupa staff users, so we just keep waiting.
        self.subscription.raise_state(SubsState.EXPECTING_PAY)
        self.transaction.ended = False
        self.subscription.position = queue.add()
        self.subscription.waiting = False  # reset wait
        self.subscription.waiting = True

    @status_callback.register('pago', 'disponivel')
    def status_callback(self, queue: QueueAgent, notify: Notifier, **_):
        # Escrow starts at 'pago' and ends at 'disponivel'. We'll assume that it will always complete
        # sucessfully because we're optimistic like that. See the dispute section.
        if self.transaction.end(sucessfully=True):
            self.subscription.position = queue.add()
            notify.confirmed()

    @status_callback.register('em_disputa')
    def status_callback(self, **_):
        # The payment is being disputed. We'll deal with this conservatively, putting the subscriber back into
        # the queue. I have no idea if this is the best approach, because we've used PagSeguro for 7 years and
        # we haven't even once got a dispute.
        self.transaction.ended = False
        self.transaction.accepted = False
        self.subscription.state = SubsState.EXPECTING_PAY
        self.subscription.waiting = True
        # pay.queue.remove(); subscription.position = queue.add()  # unsure if necessary

    @status_callback.register('devolvido', 'cancelado')
    def status_callback(self, queue: QueueAgent, notify: Notifier, **_):
        # We have to be careful here wether we have other pending transactions. So we'll first close this
        # transaction, then peek other transactions before making any changes to the subscription.
        if self.transaction.end(sucessfully=False):
            queue.remove()
            notify.pay_denied()


class CallbackDictionary(dict):
    def register(self, *keys):
        def x(func) -> CallbackDictionary:
            for key in keys:
                self[key] = func
            return self

        return x
