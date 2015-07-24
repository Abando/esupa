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
from decimal import Decimal

from django import forms
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.timezone import now

from .base import PaymentBase
from ..models import Transaction, SubsState
from ..utils import prg_redirect

log = getLogger(__name__)


class PaymentMethod(PaymentBase):
    CODE = 1
    TITLE = 'Depósito Bancário'

    def start_payment(self, request: HttpRequest, amount) -> HttpResponse:
        self.transaction = self.transactions(method=self.CODE, filled_at__isnull=True).first()
        # If the transaction above is set to None, the call below will automatically create a new one.
        self.transaction.amount = amount
        self.transaction.save()
        context = {
            'event': self.subscription.event,
            'sub': self.subscription,
            'trans': self.transaction,
            'form': DepositForm(self.transaction),
        }
        return render(request, 'esupa/deposit.html', context)

    @classmethod
    def class_view(cls, request: HttpRequest) -> HttpResponse:
        if not request.user or 'tid' not in request.POST:
            raise PermissionDenied
        transaction = Transaction.objects.get(id=int(request.POST['tid']))
        if transaction.subscription.user != request.user:
            raise SuspiciousOperation
        elif 'upload' in request.FILES:
            if transaction.subscription.state == SubsState.QUEUED_FOR_PAY:
                raise PermissionDenied
            payment = PaymentMethod(transaction)
            payment.put_file(request.FILES['upload'], request.POST['amount'])
            return prg_redirect(payment.my_view_url(request))
        else:
            return PaymentMethod(transaction).start_payment(request, transaction.amount)

    def put_file(self, upload, amount):
        transaction = self.transaction
        transaction.mimetype = upload.content_type or 'application/octet-stream'
        transaction.document = upload.read()
        transaction.filled_at = now()
        transaction.amount = Decimal(amount)
        transaction.save()
        transaction.subscription.raise_state(SubsState.VERIFYING_PAY)
        transaction.subscription.save()


class DepositForm(forms.Form):
    amount = forms.DecimalField(label='Valor depositado', max_digits=7, decimal_places=2)
    upload = forms.FileField(label='Comprovante')

    def __init__(self, transaction: Transaction, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        subscription = transaction.subscription
        fmt = 'Deposite até R$ %s na conta abaixo e envie foto ou scan do comprovante.\n%s'
        msg = fmt % (subscription.price, subscription.event.deposit_info)
        self.fields['upload'].help_text = msg.replace('\n', '\n<br/>')
        self.fields['amount'].initial = transaction.amount
