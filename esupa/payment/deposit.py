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

from django import forms
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core.urlresolvers import reverse
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.timezone import now

from . import PaymentBase, PaymentMethodMeta
from ..models import Transaction

log = getLogger(__name__)


class Payment(PaymentBase):
    meta = PaymentMethodMeta(
        code=1,
        slug='deposit',
        title='Depósito Bancário',
    )

    payment_method_code = 1
    slug = 'deposit'

    def start_payment(self, amount):
        return DepositForm(self.transaction, amount)

    @classmethod
    def locate_payment(cls, request: HttpRequest) -> 'Payment':
        if not request.user or 'tid' not in request.POST:
            raise PermissionDenied
        transaction = Transaction.objects.get(id=int(request.POST['tid']))
        if transaction.subscription.user != request.user:
            raise SuspiciousOperation
        else:
            return Payment(transaction=transaction)

    def callback_view(self, request: HttpRequest) -> HttpResponse:
        if 'upload' in request.FILES:
            file = request.FILES['upload']
            self.transaction.document = file.read()
            self.transaction.mimetype = file.content_type or 'application/octet-stream'
            self.transaction.filled_at = now()
            self.transaction.save()
        else:
            redirect(reverse('esupa-subscribe'))


class DepositForm(forms.Form):
    tid = forms.HiddenInput()
    amount = forms.DecimalField(label='Valor depositado', max_digits=7, decimal_places=2)
    upload = forms.FileField(label='Comprovante')

    def __init__(self, transaction: Transaction, amount, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        subscription = transaction.subscription
        fmt = 'Deposite até R$ %s na conta abaixo e envie foto ou scan do comprovante.\n%s'
        msg = fmt % (subscription.price, subscription.event.deposit_info)
        self.fields['upload'].help_text = msg.replace('\n', '\n<br/>')
        self.fields['amount'].value = amount
        self.fields['tid'].value = transaction.id
