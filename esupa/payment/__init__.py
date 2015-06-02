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
from pkgutil import iter_modules

from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponse, HttpRequest

from ..models import Transaction, Subscription, payment_names

log = getLogger(__name__)

_payment_methods = {}
get_payment = _payment_methods.get


class PaymentMethodMeta:
    def __init__(self, code: int, title: str):
        self.code = code
        self.title = title


def load_submodules():
    if not _payment_methods:
        return
    for importer, modname, ispkg in iter_modules(__path__, __name__ + '.'):
        print('Found submodule %s; importer %s' % (modname, importer))
        try:
            module = importer.load_module(modname)
            log.debug('Imported payment module: %s', modname)
            if hasattr(module, 'Payment'):
                subclass = module.Payment
                meta = subclass.meta
                assert isinstance(meta, PaymentMethodMeta)
                _payment_methods[meta.code] = subclass
                payment_names[meta.code] = meta.title
                log.info('Loaded payment module %s: code=%d, title=%s', meta.code, modname, meta.title)
            else:
                log.warn('Missing class Payment in module: %s', modname)
        except ImportError:
            log.warn('Failed to import payment module: %s', modname)


class PaymentBase:
    _subscription = None
    _transaction = None

    meta = PaymentMethodMeta(0, '')

    def __init__(self, subscription: Subscription=None, transaction: Transaction=None):
        if not subscription and not transaction:
            pass  # nothing to do
        elif subscription and not transaction:
            self.subscription = subscription
        elif transaction and not subscription:
            self.transaction = transaction
        else:
            if transaction.subscription is None:
                transaction.subscription = subscription
            elif transaction.subscription != subscription:
                raise SuspiciousOperation
            self.transaction = transaction

    @property
    def transaction(self) -> Transaction:
        if self._transaction is None:
            self._transaction = Transaction(subscription=self._subscription, method=self.meta.code)
        return self._transaction

    @transaction.setter
    def transaction(self, value):
        if isinstance(value, Transaction):
            self._transaction = value
        elif value:
            self._transaction = Transaction.objects.get(id=int(value))
        else:
            self._transaction = None
        if self._transaction:
            self._subscription = self._transaction.subscription

    @property
    def subscription(self) -> Subscription:
        return self._subscription

    @subscription.setter
    def subscription(self, value):
        if isinstance(value, Subscription):
            self._subscription = value
        elif value:
            self._subscription = Subscription.objects.get(id=int(value))
        else:
            self._subscription = None
            self._transaction = None
        if self._subscription and self._transaction:
            if not self._transaction.id:
                self._transaction.subscription = self._subscription
            else:
                raise ValueError('Invalid change of subscription with saved transaction. tid=%d, sid=%d' %
                                 (self._transaction.id, self._subscription.id))

    def start_payment(self, amount):
        raise NotImplementedError

    @classmethod
    def class_view(cls, request: HttpRequest) -> HttpResponse:
        raise NotImplementedError
