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
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import HttpResponse, Http404, HttpRequest, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

from .forms import SubscriptionForm, UploadForm
from .models import Event, Subscription, SubsState, Transaction, PmtMethod
from .notify import Notifier
from .payment import Deposit, Processor, get_payment
from .queue import QueueAgent, cron

log = getLogger(__name__)


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


@login_required
def view_or_edit(request: HttpRequest, slug=None) -> HttpResponse:
    subscription = _get_subscription(slug, request.user)
    if subscription.id or not subscription.event.subs_open:
        return view(request, slug)
    else:
        return edit(request, slug)


@login_required
def edit(request: HttpRequest, slug=None) -> HttpResponse:
    subscription = _get_subscription(slug, request.user)
    event = subscription.event
    state = subscription.state
    queue = QueueAgent(subscription)
    formdata = request.POST if request.method == 'POST' else None
    if not subscription.id:
        subscription.email = subscription.user.email
    form = SubscriptionForm(data=formdata, instance=subscription)
    buttons = []
    context = {
        'subscription_form': form,
        'actions': buttons,
        'event': event,
        'subscription': subscription,
    }
    # display subscription information
    if not event.subs_open:
        form.freeze()
    elif (action == 'view' and not subscription.id) or (action == 'edit') or (action == 'save' and form.errors):
        buttons.append(('save', 'Salvar'))
    else:
        form.freeze()
        if SubsState.NEW <= state <= SubsState.QUEUED_FOR_PAY:
            buttons.append(('edit', 'Editar'))


@login_required
def view(request: HttpRequest, slug=None) -> HttpResponse:
    subscription = _get_subscription(slug, request.user)
    event = subscription.event
    state = subscription.state
    queue = QueueAgent(subscription)


@login_required
def pay(request: HttpRequest, slug=None) -> HttpResponse:
    subscription = _get_subscription(slug, request.user)
    event = subscription.event
    action = request.POST.get('action', default='view')
    state = subscription.state
    queue = QueueAgent(subscription)
    if action == 'pay_processor' and event.sales_open and queue.within_capacity:
        return redirect(Processor.get(subscription).generate_transaction_url())


@login_required
def subscribe(request: HttpRequest, slug=None) -> HttpResponse:
    subscription = _get_subscription(slug, request.user)
    event = subscription.event
    action = request.POST.get('action', default='view')
    state = subscription.state
    queue = QueueAgent(subscription)


    # perform appropriate saves if applicable
    if action == 'save' and form.is_valid() and SubsState.NEW <= state <= SubsState.QUEUED_FOR_PAY:
        form.save()
        s = map(str.lower, (subscription.full_name, subscription.email, subscription.document, subscription.badge))
        b = tuple(map(str.lower, filter(bool, event.data_to_be_checked.splitlines())))
        acceptable = True not in (t in d for d in s for t in b)
        subscription.state = SubsState.ACCEPTABLE if acceptable else SubsState.VERIFYING_DATA
        subscription.save()  # action=save
        if not acceptable:
            Notifier(subscription).staffer_action_required()

    # deal with payment related stuff
    context['documents'] = subscription.transaction_set.filter(filled_at__isnull=False).values(
        'id', 'filled_at', 'ended_at', 'accepted')
    state = subscription.state  # time to refresh this information!
    if SubsState.ACCEPTABLE <= state <= SubsState.VERIFYING_PAY and (event.sales_open or subscription.waiting):
        deposit = Deposit(subscription=subscription)
        if action.startswith('pay'):
            subscription.position = queue.add()
            subscription.waiting = queue.within_capacity
            subscription.raise_state(SubsState.QUEUED_FOR_PAY if subscription.waiting else SubsState.EXPECTING_PAY)
            if len(request.FILES):
                deposit.got_file(request.FILES['upload'])
                subscription.raise_state(SubsState.VERIFYING_PAY)
                Notifier(subscription).staffer_action_required()
            elif action == 'pay_deposit':
                deposit.expecting_file = True
            subscription.save()  # action=pay
        if deposit.expecting_file:
            context['upload_form'] = UploadForm(subscription)
        if action != 'edit':
            if state == SubsState.VERIFYING_PAY:
                buttons.append(('pay_deposit', 'Enviar outro comprovante'))
            elif queue.within_capacity:
                buttons.append(('pay_deposit', 'Pagar com depósito bancário'))
                buttons.append(('pay_processor', 'Pagar com PagSeguro'))
            else:
                buttons.append(('pay_none', 'Entrar na fila de pagamento'))

    # ...whew.
    context['state'] = SubsState(subscription.state)
    return render(request, 'esupa/form.html', context)


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


def cron_view(_, secret) -> HttpResponse:
    if secret != settings.ESUPA_CRON_SECRET:
        raise SuspiciousOperation
    cron()
    return HttpResponse()  # no response


@csrf_exempt
def paying(request: HttpRequest, slug) -> HttpResponse:
    payment = get_payment(slug)
    return payment.class_view(request) or HttpResponse()


@login_required
def verify(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        raise PermissionDenied
    return render(request, 'esupa/verify.html', {'events': Event.objects})


@login_required
def verify_event(request: HttpRequest, eid) -> HttpResponse:
    if not request.user.is_staff:
        raise PermissionDenied
    event = Event.objects.get(id=int(eid))
    subscriptions = event.subscription_set.order_by('-state').all()
    context = {'event': event, 'subscriptions': subscriptions, 'state': SubsState(),
               'pmethod': PmtMethod()}
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
            if Deposit(transaction=transaction).transaction.end(acceptable):
                if acceptable:
                    notify.confirmed()
                else:
                    QueueAgent(subscription).remove()
                    notify.pay_denied()
        else:
            return HttpResponseBadRequest('Invalid attempt to %s %s=%d (%s) because subscription state is %s' % (
                'accept' if acceptable else 'reject', what, oid, subscription.badge, SubsState(subscription.state)))
    return render(request, 'esupa/event-verify.html', context)
