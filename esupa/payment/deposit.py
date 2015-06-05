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

from django import forms
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core.urlresolvers import reverse
from django.http import HttpRequest, HttpResponse
from django.utils.timezone import now

from . import PaymentBase
from ..models import Transaction, SubsState
from ..utils import prg_redirect
from ..views import view

log = getLogger(__name__)


class Payment(PaymentBase):
    CODE = 1
    TITLE = 'Depósito Bancário'

    def start_payment(self, amount):
        return DepositForm(self.transaction, amount)

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
            cls.put_file(transaction, request.FILES['upload'])
            return prg_redirect(reverse(view.name, args=(transaction.subscription.event.slug,)))
        else:
            return DepositForm(transaction, data=request.POST, files=request.FILES)

    @staticmethod
    def put_file(transaction: Transaction, upload):
        transaction.document = upload.read()
        transaction.mimetype = upload.content_type or 'application/octet-stream'
        transaction.filled_at = now()
        transaction.save()
        transaction.subscription.raise_state(SubsState.VERIFYING_PAY)
        transaction.subscription.save()


class DepositForm(forms.Form):
    tid = forms.HiddenInput()
    amount = forms.DecimalField(label='Valor depositado', max_digits=7, decimal_places=2)
    upload = forms.FileField(label='Comprovante')

    def __init__(self, transaction: Transaction, amount=None, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        subscription = transaction.subscription
        fmt = 'Deposite até R$ %s na conta abaixo e envie foto ou scan do comprovante.\n%s'
        msg = fmt % (subscription.price, subscription.event.deposit_info)
        self.fields['upload'].help_text = msg.replace('\n', '\n<br/>')
        if amount:
            self.fields['amount'].value = amount
        self.fields['tid'].value = transaction.id
