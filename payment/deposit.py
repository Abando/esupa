# coding=utf-8
from logging import getLogger

from django.core.exceptions import PermissionDenied
from django.utils.timezone import now

from ..models import PmtMethod, Subscription, Transaction

log = getLogger(__name__)


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

    def got_file(self, file):
        transaction = self._get_or_create_transaction()
        transaction.document = file.read()
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
