# coding=utf-8
from logging import getLogger

# sudo -H pip3 install django-pagseguro2
from django.conf import settings
from django.core.urlresolvers import reverse
from pagseguro import views
from pagseguro.api import PagSeguroApi, PagSeguroItem
from pagseguro.settings import TRANSACTION_STATUS
from pagseguro.signals import notificacao_recebida

from . import Processor
from ..models import SubsState, Transaction
from ..notify import Notifier
from ..queue import QueueAgent

log = getLogger(__name__)


class PagSeguroProcessor(Processor):
    slug = 'pagseguro'

    @classmethod
    def static_init(cls):
        notificacao_recebida.connect(PagSeguroProcessor.receive_notification)

    @staticmethod
    def view(request):
        return views.receive_notification(request)
        # this will circle over through pagseguro's event dispatch according to the signal we connected at static_init

    @staticmethod
    def receive_notification(transaction, **_):
        tid = int(transaction['reference'])
        esupa_transaction = Transaction.objects.get(id=tid)
        PagSeguroProcessor(esupa_transaction).handle_notification(transaction)

    def __init__(self, transaction: Transaction):
        self.t = transaction

    def generate_transaction_url(self) -> str:
        event = self.t.subscription.event
        api = PagSeguroApi()
        api.params['reference'] = self.t.id
        api.params['notificationURL'] = settings.BASE_PUBLIC_URI + reverse('esupa-processor', args=['pagseguro'])
        log.debug('Set notification URI: %s', api.params['notificationURL'])
        api.add_item(PagSeguroItem(id='e%d' % event.id, description=event.name,
                                   amount=event.price, quantity=1))
        for optional in self.t.subscription.optionals.all():
            api.add_item(PagSeguroItem(id='o%d' % optional.id, description=optional.name,
                                       amount=optional.price, quantity=1))
        data = api.checkout()
        if data['success']:
            return data['redirect_url']
        else:
            log.error('Data returned error. %s', repr(data))
            raise ValueError('PagSeguro denied pay. %s' % repr(data))

    def handle_notification(self, data: dict):
        subscription = self.t.subscription
        try:
            self.t.remote_identifier = data['code']
            self.t.notes += '\n[%s] %s %s' % (data['lastEventDate'], data['code'], data['status'])
            queue = QueueAgent(subscription)
            notify = Notifier(subscription)
            # pagseguro.models.TRANSACTION_STATUS_CHOICES:
            # aguardando, em_analise, pago, disponivel, em_disputa, devolvido, cancelado
            status = TRANSACTION_STATUS[data['status']]
            if status in ['aguardando', 'em_analise']:
                # This bit of logic is not strictly needed. I'm just making sure data is still sane.
                # 'em_analise' means PagSeguro is verifying pay, not esupa staff users, so we just keep waiting.
                subscription.raise_state(SubsState.EXPECTING_PAY)
                self.t.ended = False
                subscription.position = queue.add()
                subscription.waiting = False  # reset wait
                subscription.waiting = True
            elif status in ['pago', 'disponivel']:
                # Escrow starts at 'pago' and ends at 'disponivel'. We'll assume that it will always complete
                # sucessfully because we're optimistic like that. See the dispute section.
                if self.t.end(sucessfully=True):
                    subscription.position = queue.add()
                    notify.confirmed()
            elif status in ['em_disputa']:
                # The payment is being disputed. We'll deal with this conservatively, putting the subscriber back into
                # the queue. I have no idea if this is the best approach, because we've used PagSeguro for 7 years and
                # we haven't even once got a dispute.
                self.t.ended = False
                self.t.accepted = False
                subscription.state = SubsState.EXPECTING_PAY
                subscription.waiting = True
                # queue.remove(); subscription.position = queue.add()  # unsure if necessary
            elif status in ['devolvido', 'cancelado']:
                # We have to be careful here wether we have other pending transactions. So we'll first close this
                # transaction, then peek other transactions before making any changes to the subscription.
                if self.t.end(sucessfully=False):
                    queue.remove()
                    notify.pay_denied()
            else:
                raise ValueError('Unknown PagSeguro status code: %s' % status)
        finally:
            # No rollbacks please!
            self.t.save()
            subscription.save()
