# coding=utf-8
from logging import getLogger

from django.core.exceptions import PermissionDenied
from django.utils.timezone import now

from ..models import PmtMethod, Subscription, Transaction

log = getLogger(__name__)


class Deposit:
    def __init__(self, subscription: Subscription=None, transaction: Transaction=None):
        if transaction:
            subscription = transaction.subscription
        if not subscription.id:
            raise PermissionDenied('Payment without subscription.')
        self.subscription = subscription
        self.transaction = transaction
        self.slot_qs = subscription.transaction_set.filter(method=PmtMethod.DEPOSIT, filled_at__isnull=True)

    @property
    def expecting_file(self):
        return self.slot_qs.exists()

    def got_file(self, file):
        self._ensure_transaction()
        self.transaction.document = file.read()
        self.transaction.filled_at = now()
        self.transaction.save()

    def register_intent(self):
        self._ensure_transaction()
        self.transaction.save()

    def accept(self, acceptable):
        self._ensure_transaction()
        self.transaction.accepted = acceptable
        self.transaction.ended_at = now()
        self.transaction.save()

    def _ensure_transaction(self):
        if not self.transaction:
            self.transaction = self.slot_qs.first() or Transaction(
                subscription=self.subscription, value=self.subscription.price, method=PmtMethod.DEPOSIT)
