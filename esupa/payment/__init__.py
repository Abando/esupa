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
from pkgutil import iter_modules

from django.http import HttpResponse, HttpRequest

from ..models import Transaction, Subscription

log = getLogger(__name__)

_implementation_by_slug = {}
_implementation_by_code = {}
_subclasses_loaded = False


class PaymentBase:
    _subscription = None
    _transaction = None

    payment_method_code = 0
    slug = None

    @staticmethod
    def static_init():
        if _subclasses_loaded:
            return  # avoid double run
        for importer, modname, ispkg in iter_modules(__path__, __name__ + '.'):
            print('Found submodule %s; importer %s' % (modname, importer))
            try:
                module = importer.load_module(modname)
                log.debug('Imported payment module: %s', modname)
                if hasattr(module, 'Payment'):
                    subclass = module.Payment
                    assert issubclass(subclass, PaymentBase)
                    if not subclass.slug:
                        subclass.slug = modname
                    _implementation_by_slug[subclass.slug] = subclass
                    _implementation_by_code[subclass.payment_method_code] = subclass
                    log.info('Loaded payment module #%d, slug=%s', subclass.payment_method_code, subclass.slug)
                else:
                    log.warn('Missing class Payment in module: %s', modname)
            except ImportError:
                log.warn('Failed to import payment module: %s', modname)

    @staticmethod
    def get(slug: str) -> 'PaymentBase':
        return _implementation_by_slug[slug]

    @property
    def transaction(self) -> Transaction:
        if self._transaction is None:
            self._transaction = Transaction(subscription=self._subscription, method=self.payment_method_code)
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
    def callback_view(cls, request: HttpRequest) -> HttpResponse:
        raise NotImplementedError
