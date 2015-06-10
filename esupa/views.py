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

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core.urlresolvers import reverse
from django.forms import Form
from django.http import HttpResponse, Http404, HttpRequest, HttpResponseBadRequest
from django.shortcuts import render
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

from .forms import SubscriptionForm
from .models import Event, Subscription, SubsState, Transaction, payment_names
from .notify import Notifier
from .payment import PaymentBase, get_payment
from .queue import cron
from .utils import named

log = getLogger(__name__)

BLANK_PAGE = HttpResponse()


def _get_subscription(event_slug: str, user: User) -> Subscription:
    """Takes existing subscription if available, creates a new one otherwise."""
    if event_slug:
        event = Event.objects.get(slug=event_slug)
    else:
        # find closest event in the future
        event = Event.objects.filter(starts_at__gt=now()).order_by('starts_at').first()
        if not event:
            # find closest event in the past
            event = Event.objects.filter(starts_at__lt=now()).order_by('-starts_at').first()
        if not event:
            raise Http404('There is no event. Create one in /admin/')
    queryset = Subscription.objects
    queryset = queryset.filter(event=event, user=user)
    result = queryset.first()
    if not result:
        result = Subscription(event=event, user=user)
    elif result.state == SubsState.DENIED:
        raise PermissionDenied
    return result


@named('esupa-view')
@login_required
def view(request: HttpRequest, slug=None) -> HttpResponse:
    subscription = _get_subscription(slug, request.user)
    if subscription.id:
        context = {
            'sub': subscription,
            'event': subscription.event,
            'state': SubsState(subscription.state),
            'pay_buttons': payment_names,
            'post_to': reverse(view.name, args=[slug]),
        }
        if 'pay_with' in request.POST:
            payment = get_payment(int(request.POST['pay_with']))(subscription)
            assert isinstance(payment, PaymentBase)
            pay_info = payment.start_payment(request, subscription.price)
            if isinstance(pay_info, Form):
                context['pay_form'] = pay_info
                context['post_to'] = reverse(paying.name, args=[payment.CODE])
            elif isinstance(pay_info, HttpResponse):
                return pay_info
            else:
                raise NotImplementedError  # I'm not sure what to do here...
        return render(request, 'esupa/view.html', context)
    elif request.POST:
        # Avoid an infinite loop. We shouldn't be receiving a POST in this view without a preexisting Subscription.
        raise SuspiciousOperation
    else:
        return edit(request, slug)  # may call view(); it's probably a bug if it does


@named('esupa-edit')
@login_required
def edit(request: HttpRequest, slug=None) -> HttpResponse:
    subscription = _get_subscription(slug, request.user)
    if subscription.state > SubsState.QUEUED_FOR_PAY:
        return view(request, slug)  # may call edit(); it's probably a bug if it does
    if not subscription.id:
        subscription.email = subscription.user.email
    form = SubscriptionForm(data=request.POST or None, instance=subscription)
    if request.POST and form.is_valid() and SubsState.NEW <= subscription.state <= SubsState.QUEUED_FOR_PAY:
        form.save()
        s = map(str.lower, (subscription.full_name, subscription.email, subscription.document, subscription.badge))
        b = tuple(map(str.lower, filter(bool, subscription.event.data_to_be_checked.splitlines())))
        acceptable = True not in (t in d for d in s for t in b)
        subscription.state = SubsState.ACCEPTABLE if acceptable else SubsState.VERIFYING_DATA
        subscription.save()
        if not acceptable:
            Notifier(subscription).staffer_action_required()
        return view(request, slug)  # may call edit(); it's probably a bug if it does
    else:
        return render(request, 'esupa/edit.html', {
            'form': form,
            'event': subscription.event,
            'subscription': subscription,
        })


@named('esupa-trans-doc')
@login_required
def transaction_document(request: HttpRequest, tid) -> HttpResponse:
    # Add ETag generation & verification… maybe… eventually…
    trans = Transaction.objects.get(id=tid)
    if trans is None or not trans.document:
        raise Http404("No such document.")
    if not request.user.is_staff and trans.subscription.user != request.user:
        return PermissionDenied
    response = HttpResponse(trans.document, content_type=trans.mimetype)
    return response


@named('esupa-cron')
def cron_view(_, secret) -> HttpResponse:
    if secret != settings.ESUPA_CRON_SECRET:
        raise SuspiciousOperation
    cron()
    return BLANK_PAGE


@named('esupa-pay')
@csrf_exempt
def paying(request: HttpRequest, code) -> HttpResponse:
    resolved_view = get_payment(int(code)).class_view
    return resolved_view(request) or BLANK_PAGE


@named('esupa-verify')
@login_required
def verify(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        raise PermissionDenied
    return render(request, 'esupa/verify.html', {'events': Event.objects})


@named('esupa-verify-event')
@login_required
def verify_event(request: HttpRequest, eid) -> HttpResponse:
    if not request.user.is_staff:
        raise PermissionDenied
    event = Event.objects.get(id=int(eid))
    subscriptions = event.subscription_set.order_by('-state').all()
    context = {'event': event, 'subscriptions': subscriptions, 'state': SubsState(),
               'pmethod': '?'}  # FIXME
    if request.method == 'POST':
        what, oid, acceptable = request.POST['action'].split()
        oid, acceptable = int(oid), (acceptable == 'ok')
        if what == 's':
            subscription = Subscription.objects.get(id=oid)
            transaction = None
        else:
            transaction = Transaction.objects.get(id=oid)
            subscription = transaction.subscription
        notify = Notifier(subscription)
        # the logic here is a bit too mixed. we might want to separate concerns more clearly.
        if subscription.state == SubsState.VERIFYING_DATA:
            if acceptable:
                subscription.state = SubsState.ACCEPTABLE
                subscription.save()
                notify.can_pay()
            else:
                subscription.state = SubsState.DENIED
                subscription.save()
                notify.data_denied()
        elif subscription.state >= SubsState.ACCEPTABLE:
            raise NotImplementedError  # FIXME
            # if Deposit(transaction=transaction).transaction.end(acceptable):
            #     if acceptable:
            #         notify.confirmed()
            #     else:
            #         QueueAgent(subscription).remove()
            #         notify.pay_denied()
        else:
            return HttpResponseBadRequest('Invalid attempt to %s %s=%d (%s) because subscription state is %s' % (
                'accept' if acceptable else 'reject', what, oid, subscription.badge, SubsState(subscription.state)))
    return render(request, 'esupa/event-verify.html', context)
