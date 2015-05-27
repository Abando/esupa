# coding=utf-8
#
# Copyright 2015, Abando.
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

from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile
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
        self._transaction = transaction
        self._slot_qs = subscription.transaction_set.filter(method=PmtMethod.DEPOSIT, filled_at__isnull=True)

    def got_file(self, file: UploadedFile):
        log.debug('Got file: %s', repr(file))
        self.transaction.document = file.read()
        self.transaction.mimetype = file.content_type or 'application/octet-stream'
        self.transaction.filled_at = now()
        self.transaction.save()

    @property
    def expecting_file(self) -> bool:
        return self._slot_qs.exists()

    @expecting_file.setter
    def expecting_file(self, value: bool):
        if value:
            self.transaction.save()
        else:
            self._slot_qs.delete()

    @property
    def transaction(self) -> Transaction:
        if not self._transaction:
            self._transaction = self._slot_qs.first() or Transaction(
                subscription=self.subscription, value=self.subscription.price, method=PmtMethod.DEPOSIT)
        return self._transaction
