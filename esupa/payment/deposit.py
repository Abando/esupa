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
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest, HttpResponse
from django.utils.crypto import salted_hmac, get_random_string

from django.utils.timezone import now

from . import PaymentBase
from ..models import Subscription, Transaction

log = getLogger(__name__)

SALT_LEN = 12


class Payment(PaymentBase):
    payment_method_code = 1
    slug = 'deposit'

    def start_payment(self, amount):
        return DepositForm(self.subscription)

    @classmethod
    def callback_view(cls, request: HttpRequest) -> HttpResponse:
        log.debug('Got file: %s', repr(file))
        self.transaction.document = file.read()
        self.transaction.mimetype = file.content_type or 'application/octet-stream'
        self.transaction.filled_at = now()
        self.transaction.save()


class DepositForm(forms.Form):
    tid = forms.HiddenInput()
    tid_hash = forms.HiddenInput()
    amount = forms.DecimalField(label='Valor depositado', max_digits=7, decimal_places=2)
    upload = forms.FileField(label='Comprovante')

    def __init__(self, transaction, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        subscription = transaction.subscription
        price = subscription.price
        fmt = 'Deposite até R$ %s na conta abaixo e envie foto ou scan do comprovante.\n%s'
        msg = fmt % (subscription.price, subscription.event.deposit_info)
        self.fields['upload'].help_text = msg.replace('\n', '\n<br/>')
        self.fields['amount'].value = price
        self.fields['tid'].value = transaction.id
        self.fields['tid_hash'].value = _tid_hash(transaction.id)


def _tid_hash(tid, salt=None):
    salt = salt[:SALT_LEN] if salt else get_random_string(SALT_LEN)
    return salt + salted_hmac(salt, tid).hexdigest()