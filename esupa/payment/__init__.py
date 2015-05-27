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

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest

from ..models import PmtMethod
from .deposit import Deposit

logger = getLogger(__name__)


class Processor:
    _initialized = False
    _processors = {}
    slug = None

    @classmethod
    def static_init(cls):
        if not cls._initialized:
            if hasattr(settings, 'PAGSEGURO_EMAIL'):
                from .pagseguro import PagSeguroProcessor

                PagSeguroProcessor.static_init()
                cls._processors[PagSeguroProcessor.slug] = PagSeguroProcessor
            cls._initialized = True

    @classmethod
    def get(cls, subscription):
        cls.static_init()
        if not subscription.id:
            raise PermissionDenied('Payment without subscription.')
        tset = subscription.transaction_set
        transaction = tset.filter(method=PmtMethod.PAGSEGURO, filled_at__isnull=True).first() or \
            tset.create(subscription=subscription, value=subscription.price, method=PmtMethod.PAGSEGURO)
        processor_slug = 'pagseguro'  # TODO: add a selector, somehow (no idea how)
        processors = cls._processors
        processor = processors[processor_slug]
        return processor(transaction)

    @classmethod
    def dispatch_view(cls, slug, request):
        cls.static_init()
        processor = cls._processors.get(slug)
        if issubclass(processor, cls):
            return processor.view(request)
        else:
            return HttpResponseBadRequest()

    def generate_transaction_url(self):
        raise NotImplementedError()
