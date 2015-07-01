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
from json import loads
from logging import getLogger

# https://developer.paypal.com/webapps/developer/docs/integration/web/web-checkout/
# sudo -H pip3 install paypalrestsdk
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.http import HttpRequest
from paypalrestsdk import configure, Payment  # sudo -H pip3 install paypalrestsdk

from .base import PaymentBase
from ..notify import Notifier
from ..queue import QueueAgent
from ..utils import FunctionDictionary, prg_redirect

log = getLogger(__name__)

# Step 2 of 5
EXAMPLE_OF_STEP_2 = {
    "id": "PAY-4KH58796UL7314635KWBOD2Y",
    "create_time": "2015-06-18T15:21:15Z",
    "update_time": "2015-06-18T15:21:15Z",
    "state": "created",
    "intent": "sale",
    "payer": {"payment_method": "paypal",
              "payer_info": {"shipping_address": {}}},
    "transactions": [{"amount": {"total": "12.00",
                                 "currency": "USD",
                                 "details": {"subtotal": "12.00"}},
                      "description": "creating a payment",
                      "related_resources": []}],
    "links": [{"href": "https://api.sandbox.paypal.com/v1/payments/payment/PAY-4KH58796UL7314635KWBOD2Y",
               "rel": "self",
               "method": "GET"},
              {"href": "https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=EC-06V91777NR989274B",
               "rel": "approval_url",
               "method": "REDIRECT"},
              {"href": "https://api.sandbox.paypal.com/v1/payments/payment/PAY-4KH58796UL7314635KWBOD2Y/execute",
               "rel": "execute",
               "method": "POST"}]}
# Step 3 of 5
# Take the approval url from the response JSON, and redirect the user to paypal for approval
# Step 4 of 5
# Execute a payment by constructing a payment object with payment id and use the payer id returned
# from PayPal and make the API call using the access token
# payment = paypalrestsdk.Payment.find("PAY-8E794821851241408KWBRMLA")
# payment.execute({"payer_id": "88PNNFBXL6PZS"}) 
# VISA 4222222222222
# A JSON response will be returned :
EXAMPLE_OF_STEP_4 = {
    "id": "PAY-8E794821851241408KWBRMLA",
    "create_time": "2015-06-18T19:04:12Z",
    "update_time": "2015-06-18T20:01:50Z",
    "state": "approved",
    "intent": "sale",
    "payer": {"payment_method": "paypal",
              "payer_info": {"email": "usa@ekevoo.com",
                             "first_name": "Yankee",
                             "last_name": "Murica",
                             "payer_id": "88PNNFBXL6PZS",
                             "shipping_address": {"line1": "1 Main St",
                                                  "city": "San Jose",
                                                  "state": "CA",
                                                  "postal_code": "95131",
                                                  "country_code": "US",
                                                  "recipient_name": "Yankee Murica"}}},
    "transactions": [{
        "amount": {"total": "12.00",
                   "currency": "USD",
                   "details": {"subtotal": "12.00"}},
        "description": "creating a payment",
        "related_resources": [{"sale": {
            "id": "9P7720498T958842D",
            "create_time": "2015-06-18T19:04:12Z",
            "update_time": "2015-06-18T20:01:51Z",
            "amount": {"total": "12.00",
                       "currency": "USD"},
            "payment_mode": "INSTANT_TRANSFER",
            "state": "completed",
            "protection_eligibility": "ELIGIBLE",
            "protection_eligibility_type": "ITEM_NOT_RECEIVED_ELIGIBLE,UNAUTHORIZED_PAYMENT_ELIGIBLE",
            "parent_payment": "PAY-8E794821851241408KWBRMLA",
            "transaction_fee": {"value": "0.65",
                                "currency": "USD"},
            "links": [{"href": "https://api.sandbox.paypal.com/v1/payments/sale/9P7720498T958842D",
                       "rel": "self",
                       "method": "GET"},
                      {"href": "https://api.sandbox.paypal.com/v1/payments/sale/9P7720498T958842D/refund",
                       "rel": "refund",
                       "method": "POST"},
                      {"href": "https://api.sandbox.paypal.com/v1/payments/payment/PAY-8E794821851241408KWBRMLA",
                       "rel": "parent_payment",
                       "method": "GET"}]}}]}],
    "links": [{"href": "https://api.sandbox.paypal.com/v1/payments/payment/PAY-8E794821851241408KWBRMLA",
               "rel": "self",
               "method": "GET"}]}
# Step 5 of 5
# Payment Completed for Payment Id: PAY-8E794821851241408KWBRMLA
# Payment Status: approved

def _find_href(links, rel):
    for link in links:
        if link.get('rel') == rel:
            return link['href']
    raise KeyError


class PaymentMethod(PaymentBase):
    CODE = 3
    TITLE = 'PayPal'
    CONFIGURATION_KEYS = ('PAYPAL',)

    @classmethod
    def static_init(cls, app_config, my_module):
        super().static_init(app_config, my_module)
        configure(settings.PAYPAL)  # https://developer.paypal.com/developer/applications
        # Sample settings:
        _ = {'mode': 'sandbox',
             'client_id': 'AQkquBDf1zctJOWGKWUEtKXm6qVhueUEMvXO_-MCI4DQQ4-LWvkDLIN2fGsd',
             'client_secret': 'EL1tVxAjhT7cJimnz5-Nsx9k2reTKSVfErNQF-CmrwJgxRtylkGTKlU4RvrX'}

    def start_payment(self, request, amount):
        event = self.subscription.event
        self.transaction.value = amount
        payment = Payment({
            'transactions': [{'amount': {'total': amount,
                                         'currency': 'BRL'},
                              'description': event.name}],
            'payer': {'payment_method': 'paypal'},
            'redirect_urls': {'return_url': self.my_pay_url(request),
                              'cancel_url': self.my_view_url(request)},
            'intent': 'sale'})
        result = loads(payment.create())
        if result:
            self.transaction.remote_identifier = result['id']
            self.transaction.save()
            return _find_href(result['links'], 'approval_url')
        else:
            log.error('Data returned error. %s', repr(result))
            raise ValueError('PayPal denied pay. %s' % repr(result))

    @classmethod
    def class_view(cls, request: HttpRequest):
        payment_id = request.GET.get('paymentId')
        payer_id = request.GET.get('PayerID')
        if not payment_id:
            raise SuspiciousOperation
        payment = PaymentMethod(payment_id)
        paypal = Payment.find(payment_id)
        result = paypal.execute({'payer_id': payer_id})
        payment.callback_view(result)
        # This is actually the user here, not a callback bot! So we must return to base.
        # TODO: What if the user never returns home after paying? Should we poll pending transactions?
        return prg_redirect(payment.my_view_url(request))

    def callback_view(self, data: dict):
        try:
            self.transaction.notes += '\n[%s] %s %s' % (data['lastEventDate'], data['code'], data['status'])
            queue = QueueAgent(self.subscription)
            notify = Notifier(self.subscription)
            state = data['state']
            self.state_callback.get(state)(self, state=state, queue=queue, notify=notify)
        finally:
            # No rollbacks please!
            self.transaction.save()
            self.subscription.save()

    @FunctionDictionary
    def state_callback(self, **kwargs):
        log.debug(repr(kwargs))

    @state_callback.register('approved')
    def state_callback(self, queue: QueueAgent, notify: Notifier, **_):
        if self.transaction.end(sucessfully=True):
            self.subscription.position = queue.add()
            notify.confirmed()
