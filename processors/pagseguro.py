# coding=utf-8
from logging import getLogger

from pagseguro import views
from pagseguro.api import PagSeguroApi, PagSeguroItem
from pagseguro.models import Transaction as PagSeguroTransaction
from pagseguro.signals import notificacao_recebida

from ..models import Transaction as EsupaTransaction
from ..payment import Processor


logger = getLogger(__name__)


class PagSeguroProcessor(Processor):
    @classmethod
    def static_init(cls):
        notificacao_recebida.connect(PagSeguroProcessor.receive_notification)

    @staticmethod
    def view(request):
        return views.receive_notification(request)
        # this will circle over through pagseguro's event dispatch according to the signal we connected at static_init

    @staticmethod
    def receive_notification(transaction, sender=None):
        assert isinstance(transaction, PagSeguroTransaction)
        assert isinstance(sender, PagSeguroApi)
        tid = int(transaction.reference)
        esupa_transaction = EsupaTransaction.objects.get(id=tid)
        PagSeguroProcessor(esupa_transaction).handle_notification(transaction)

    def __init__(self, transaction):
        assert isinstance(transaction, EsupaTransaction)
        self.t = transaction

    def generate_transaction_url(self) -> str:
        event = self.t.subscription.event
        api = PagSeguroApi(self.t.id)
        api.add_item(PagSeguroItem(id='e%d' % event.id, description=event.name,
                                   amount=event.price, quantity=1))
        for optional in self.t.subscription.optionals:
            api.add_item(PagSeguroItem(id='o%d' % optional.id, description=optional.name,
                                       amount=optional.price, quantity=1))
        data = api.checkout()
        if data['success']:
            return data['redirect_url']
        else:
            logger.error('Data returned error. %s', repr(data))
            raise ValueError()  # TODO: signal this error some better way

    def handle_notification(self, pagseguro_transaction):
        pass
