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
from random import randint
from threading import Thread

from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse

from .models import Subscription

log = getLogger(__name__)


def _mail(recipients, subject, body):
    it = 'mail#%d' % randint(0, 0x10000)
    def mail():
        try:
            log.info("Trying to send %s to %s about %s", it, ','.join(recipients), subject)
            EmailMessage(subject, body, to=recipients).send(fail_silently=True)
            log.info("Sent %s alright", it)
        except ConnectionRefusedError:
            log.error("Connection failed for %s to %s", it, ','.join(recipients), exc_info=True)

    Thread(target=mail, name=it).start()  # this will come back to bite our butt, rest assured.


class Notifier:
    def __init__(self, subscription):
        assert isinstance(subscription, Subscription)
        self.s = subscription

    def _send(self, subject, *body):
        event = self.s.event
        subject = '%s - %s' % (subject, event.name)
        body = (self.s.badge + ',', '') + body + ('', '=' * len(event.name), event.name)
        _mail([self.s.email], subject, body)

    def can_pay(self):
        """This can happen in two cases, (1) esupa staff data verify accepted, or (2) the queue moved."""
        self._send('Pagamento Liberado',
                   'Sua inscrição está pronta para ser paga. Após o pagamento, ela será',
                   'confirmada, e sua vaga estará garantida.')

    def expired(self):
        """This means we've waited too long and the subscription can no longer be paid."""
        hours = self.s.event.payment_wait_hours
        self._send('Pagamento Vencida',
                   'O seu prazo de %d horas para pagar venceu e você foi retirado da' % hours,
                   'fila de pagamento.')

    def data_denied(self):
        """Esupa staff data verify failed."""
        self._send('Inscrição Negada',
                   'Seus dados foram verificados e sua inscrição foi negada.')

    def confirmed(self):
        """Pay has been accepted."""
        self._send('Inscriçao Confirmada',
                   'Bem vindo! Sua inscrição está confirmada. :)')

    def pay_denied(self):
        """Pay has been denied by the processor."""
        self._send('Pagamento Cancelado',
                   'O seu pagamento foi cancelado pela operadora de pagamento.')

    def staffer_action_required(self):
        """Sent to staffers, telling them that they're supposed to verify some data."""
        subject = '[%s] verificar: %s' % (self.s.event.name, self.s.badge)
        body = 'Verificar inscrição #%d (%s): %s' % (
            self.s.id, self.s.badge, reverse('esupa-verify-event', args=[self.s.event.id]))
        recipients = User.objects.filter(is_staff=True).values_list('email', flat=True)
        _mail(recipients, subject, body)


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
