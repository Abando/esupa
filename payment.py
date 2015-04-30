# coding=utf-8
from logging import getLogger

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.utils.timezone import now

from .models import PmtMethod, Subscription, Transaction

logger = getLogger(__name__)

# TODO: this should be some decent dependency injection instead
if hasattr(settings, 'PAGSEGURO_EMAIL'):
    from .processors.pagseguro import PagSeguroProcessor
else:
    PagSeguroProcessor = None


class Processor:
    @classmethod
    def static_init(cls):
        if PagSeguroProcessor:
            PagSeguroProcessor.static_init()

    @classmethod
    def get(cls, subscription):
        if not subscription.id:
            raise PermissionDenied('Payment without subscription.')
        tset = subscription.transaction_set
        transaction = tset.filter(method=PmtMethod.PAGSEGURO, filled_at__isnull=True).first() or \
            tset.create(subscription=subscription, value=subscription.price, method=PmtMethod.PAGSEGURO)
        # Add support for other processors here.
        return PagSeguroProcessor(transaction)

    @staticmethod
    def dispatch_view(slug, request):
        if slug == 'pagseguro':
            return PagSeguroProcessor.view(request)
        else:
            return HttpResponseBadRequest()

    def generate_transaction_url(self):
        raise NotImplementedError()


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
        transaction.filled_at = now()
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
        transaction.ended_at = now()
        transaction.save()


Processor.static_init()
