# -*- coding: utf-8 -*-
#
# Copyright 2015, Ekevoo.com.
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
from importlib import import_module
from logging import getLogger
from os.path import dirname
from pkgutil import walk_packages

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import QuerySet
from django.http import HttpResponse, HttpRequest

from ..models import Transaction, Subscription

log = getLogger(__name__)

payment_methods = {}
payment_names = {}


class PaymentBase:
    CODE = 0
    TITLE = ''
    CONFIGURATION_KEYS = ()

    @classmethod
    def static_init(cls):
        is_missing = lambda key: not hasattr(settings, key)
        missing = tuple(filter(is_missing, cls.CONFIGURATION_KEYS))
        if missing:
            raise NoConfiguration(missing)

    _subscription = None
    _transaction = None

    def __init__(self, subscription_or_transaction_or_remote_id):
        if not subscription_or_transaction_or_remote_id:
            pass  # nothing to do
        elif isinstance(subscription_or_transaction_or_remote_id, Subscription):
            self.subscription = subscription_or_transaction_or_remote_id
        elif isinstance(subscription_or_transaction_or_remote_id, Transaction):
            self.transaction = subscription_or_transaction_or_remote_id
        elif isinstance(subscription_or_transaction_or_remote_id, str):
            self.transaction = Transaction.objects.get(
                method=self.CODE, remote_identifier=subscription_or_transaction_or_remote_id)
        else:
            raise ValueError

    def transactions(self, **criteria) -> QuerySet:
        return self.subscription.transaction_set.filter(**criteria)

    @property
    def transaction(self) -> Transaction:
        if self._transaction is None:
            self._transaction = Transaction(subscription=self._subscription, method=self.CODE)
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

    def start_payment(self, request, amount) -> HttpResponse:
        raise NotImplementedError

    @classmethod
    def class_view(cls, request: HttpRequest) -> HttpResponse:
        raise NotImplementedError

    def my_pay_url(self, request: HttpRequest) -> str:
        from ..views import paying

        return request.build_absolute_uri(reverse(paying.name, args=(self.CODE,)))

    def my_view_url(self, request: HttpRequest):
        from ..views import view

        return request.build_absolute_uri(reverse(view.name, args=(self.subscription.event.slug,)))


def get_payment(code: int) -> type:
    load_submodules()
    return payment_methods[code]


def get_payment_names() -> dict:
    load_submodules()
    return payment_names


def load_submodules():
    if payment_methods:
        return
    path = dirname(__file__)
    log.debug('Will traverse %s', path)
    for loader, modname, ispkg in walk_packages([path]):
        log.debug('Found sub%s %s' % ('package' if ispkg else 'module', modname))
        try:
            module = import_module(__name__[:-4] + modname)
            log.debug('Imported payment module: %s', modname)
            if hasattr(module, 'PaymentMethod'):
                subclass = module.PaymentMethod
                subclass.static_init()
                payment_methods[subclass.CODE] = subclass
                payment_names[subclass.CODE] = subclass.TITLE
                log.info('Payment module %s loaded: code=%d, title=%s', modname, subclass.CODE, subclass.TITLE)
            else:
                log.debug('No class PaymentMethod in module: %s', modname)
        except NoConfiguration as e:
            log.info('Payment module %s disabled due to missing configuration: %s', modname, ', '.join(e.keys))
        except ImportError as e:
            log.warn('Failed to import payment module %s: %s', modname, e.msg)
        except SyntaxError as e:
            log.warn('Failed to import payment module %s', modname)
            log.debug(e, exc_info=True)


class NoConfiguration(Exception):
    def __init__(self, keys, *args, **kwargs):
        self.keys = keys
        super().__init__(*args, **kwargs)
