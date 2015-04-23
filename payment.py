# coding=utf-8
from datetime import datetime
from django.core.exceptions import PermissionDenied
from esupa.models import Subscription, Transaction, PmtMethod, SubsState


class PagSeguroProcessor:
    def __init__(self, subscription):
        if not subscription.id:
            raise PermissionDenied('Payment without subscription.')
        self.s = subscription

    def start_and_go(self) -> str:
        raise NotImplementedError()

    @staticmethod
    def callback(request):
        raise NotImplementedError()


def callback_pagseguro(request):
    return PagSeguroProcessor.callback(request)


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
        if self.subscription.state < SubsState.VERIFYING_PAY:
            self.subscription.state = SubsState.VERIFYING_PAY
            self.subscription.save()

    def register_intent(self):
        transaction = self._get_or_create_transaction()
        if not transaction.id:
            transaction.save()
        if self.subscription.state < SubsState.WAITING:
            self.subscription.state = SubsState.WAITING
            self.subscription.waiting = True
            self.subscription.save()

    def _get_or_create_transaction(self) -> Transaction:
        return self.slot_qs.first() or Transaction(subscription=self.subscription, value=self.subscription.price,
                                                   method=PmtMethod.DEPOSIT)
