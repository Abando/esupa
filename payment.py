# coding=utf-8
from datetime import datetime

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse

from esupa.models import PmtMethod, Subscription, Transaction


class Processor:
    def __init__(self, subscription):
        self.s = subscription
        self._cart = None

    @property
    def cart(self):
        if self._cart is None:
            self._cart = [CartItem(self.s.event)]
            self._cart.extend(map(CartItem, self.s.optionals.iterable()))
        return self._cart

    def generate_processor_url(self) -> str:
        raise NotImplementedError()


class CartItem:
    def __init__(self, other):
        # We expect Event and Optional here. Python's duck typing ahoy!
        self.id = other.id
        self.name = other.name
        self.price = other.price


class PagSeguroProcessor(Processor):
    def __init__(self, subscription):
        Processor.__init__(subscription)

    def generate_processor_url(self) -> str:
        pass

    @staticmethod
    def callback(request):
        trans = Transaction.objects.get(remote_identifier=request.FIXME.id_trans)
        #if request.FIXME
        raise NotImplementedError()


def get_processor(subscription) -> PagSeguroProcessor:
    if not subscription.id:
        raise PermissionDenied('Payment without subscription.')
    # Add support for other processors here.
    return PagSeguroProcessor(subscription)


def processor_callback(slug, request):
    if slug == 'pagseguro':
        return PagSeguroProcessor.callback(request)
    return HttpResponse(status=400)  # Bad Request


class Deposit:
    def __init__(self, subscription):
        if not subscription.id:
            raise PermissionDenied('Payment without subscription.')
        assert isinstance(subscription, Subscription)
        self.subscription = subscription
        self.slot_qs = subscription.transaction_set.filter(method=PmtMethod.DEPOSIT, filled_at__isnull=True)

    @property
    def expecting_file(self):
        return self.slot_qs.exists()

    def got_file(self, data):
        transaction = self._get_or_create_transaction()
        transaction.document = data
        transaction.filled_at = datetime.now()
        transaction.save()

    def register_intent(self):
        transaction = self._get_or_create_transaction()
        if not transaction.id:
            transaction.save()

    def _get_or_create_transaction(self) -> Transaction:
        return self.slot_qs.first() or Transaction(subscription=self.subscription, value=self.subscription.price,
                                                   method=PmtMethod.DEPOSIT)

    def accept(self, acceptable):
        transaction = self.subscription.transaction_set.get(method=PmtMethod.DEPOSIT, ended_at__isnull=True)
        transaction.accepted = acceptable
        transaction.ended_at = datetime.now()
        transaction.save()
