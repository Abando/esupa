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
from decimal import Decimal, DecimalException
from logging import getLogger

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import HttpResponse, Http404, HttpRequest, JsonResponse
from django.shortcuts import render
from django.utils.decorators import classonlymethod
from django.utils.timezone import now
from django.utils.translation import ugettext
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

from .forms import SubscriptionForm, PartialPayForm, ManualTransactionForm
from .models import Event, Subscription, SubsState, Transaction
from .notify import Notifier
from .payment.base import get_payment, get_payment_names
from .queue import cron, QueueAgent
from .utils import named, prg_redirect

log = getLogger(__name__)

BLANK_PAGE = HttpResponse()


@named('esupa-splash')
@login_required
def redirect_to_view_or_edit(request: HttpRequest, slug: str) -> HttpResponse:
    try:
        event = Event.objects.get(slug=slug)
    except Event.DoesNotExist:
        look_to_the_future = Event.objects.filter(starts_at__gt=now()).order_by('starts_at')
        look_to_the_past = Event.objects.filter(starts_at__lt=now()).order_by('-starts_at')
        event = look_to_the_future.first() or look_to_the_past.first()
    if event:
        exists = Subscription.objects.filter(event=event, user=request.user).exists()
        return prg_redirect(view.name if exists else edit.name, event.slug)
    else:
        raise Http404(ugettext('There is no event. Create one in /admin/'))


def _get_subscription(event_slug: str, user: User) -> Subscription:
    """Takes existing subscription if available, creates a new one otherwise."""
    try:
        event = Event.objects.get(slug=event_slug)
    except Event.DoesNotExist:
        raise Http404(ugettext('Unknown event %s.') % event_slug)
    kwargs = dict(event=event, user=user)
    try:
        subscription = Subscription.objects.get(**kwargs)
    except Subscription.DoesNotExist:
        subscription = Subscription(**kwargs)
    if subscription.state == SubsState.DENIED:
        raise PermissionDenied
    return subscription


@named('esupa-view')
@login_required
def view(request: HttpRequest, slug: str) -> HttpResponse:
    subscription = _get_subscription(slug, request.user)
    if subscription.id:
        context = {
            'sub': subscription,
            'event': subscription.event,
            'state': SubsState(subscription.state),
            'pending_trans': subscription.transaction_set.filter(document__isnull=False, ended_at__isnull=True),
            'confirmed_trans': subscription.transaction_set.filter(accepted=True),
            'partial_pay_form': PartialPayForm(subscription.get_owing()),
            'pay_buttons': get_payment_names(),
        }
        if 'pay_with' in request.POST:
            queue = QueueAgent(subscription)
            subscription.position = queue.add()
            subscription.waiting = queue.within_capacity
            subscription.raise_state(SubsState.EXPECTING_PAY if queue.within_capacity else SubsState.QUEUED_FOR_PAY)
            subscription.save()
            if queue.within_capacity:
                payment = get_payment(int(request.POST['pay_with']))(subscription)
                try:
                    amount = Decimal(request.POST.get('amount', ''))
                except DecimalException:
                    amount = subscription.get_owing()
                return payment.start_payment(request, amount)
        return render(request, 'esupa/view.html', context)
    else:
        return prg_redirect(edit.name, slug)


@named('esupa-edit')
@login_required
def edit(request: HttpRequest, slug: str) -> HttpResponse:
    subscription = _get_subscription(slug, request.user)
    if not subscription.id and subscription.user.email:
        subscription.email = subscription.user.email
    form = SubscriptionForm(data=request.POST or None, instance=subscription)
    if request.POST and form.is_valid():
        old_state = subscription.state
        form.save()
        s = map(str.lower, (subscription.full_name, subscription.email, subscription.document, subscription.badge))
        b = tuple(map(str.lower, filter(bool, subscription.event.data_to_be_checked.splitlines())))
        acceptable = True not in (t in d for d in s for t in b)
        if not acceptable:
            subscription.state = SubsState.VERIFYING_DATA  # Lowers the state.
        elif subscription.paid_any:
            if subscription.get_owing() <= 0:
                subscription.raise_state(SubsState.CONFIRMED)
            elif subscription.state == SubsState.CONFIRMED:
                subscription.state = SubsState.PARTIALLY_PAID  # Lowers the state.
        else:
            subscription.raise_state(SubsState.ACCEPTABLE)
        subscription.save()
        Notifier(subscription).saved(old_state, request.build_absolute_uri)
        return prg_redirect(view.name, slug)
    else:
        return render(request, 'esupa/edit.html', {
            'form': form,
            'event': subscription.event,
            'subscription': subscription,
        })


@named('esupa-trans-doc')
@login_required
def transaction_document(request: HttpRequest, tid) -> HttpResponse:
    trans = Transaction.objects.get(id=tid)
    if trans is None or not trans.document:
        raise Http404(ugettext("No such document."))
    if not request.user.is_staff and trans.subscription.user != request.user:
        return PermissionDenied
    response = HttpResponse(trans.document, content_type=trans.mimetype)
    return response


@named('esupa-cron')
def cron_view(request: HttpRequest, secret) -> HttpResponse:
    if request.user and request.user.is_staff:
        return cron() or BLANK_PAGE
    elif secret != getattr(settings, 'ESUPA_CRON_SECRET', None):
        cron()
        return BLANK_PAGE
    else:
        raise SuspiciousOperation


@named('esupa-pay')
@csrf_exempt
def paying(request: HttpRequest, code) -> HttpResponse:
    resolved_view = get_payment(int(code)).class_view
    return resolved_view(request) or BLANK_PAGE


@named('esupa-json-state')
def json_state(_: HttpRequest, slug: str) -> JsonResponse:
    result = JsonResponse(_json_state(slug))
    result['Access-Control-Allow-Origin'] = '*'
    return result


def _json_state(slug: str) -> dict:
    try:
        event = Event.objects.get(slug=slug)
    except Event.DoesNotExist:
        return {'exists': False, 'slug': slug}
    threshold = event.reveal_openings_under
    potentially = max(0, event.capacity - event.num_confirmed)
    currently = max(0, potentially - event.num_pending)
    if threshold > 0:
        potentially = str(threshold) + '+' if potentially > threshold else str(potentially)
        currently = str(threshold) + '+' if currently > threshold else str(currently)
    return {'exists': True, 'slug': slug, 'id': event.id,
            'registrationOpen': event.subs_open, 'salesOpen': event.sales_open,
            'potentiallyAvailable': potentially, 'currentlyAvailable': currently}


class EsupaListView(ListView):
    name = ''

    @classonlymethod
    def as_view(cls, **initkwargs):
        view_ = login_required(super().as_view(**initkwargs))
        view_.name = cls.name
        return view_

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        assert isinstance(user, User)
        if not user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(user=self.request.user, **kwargs)


class EventList(EsupaListView):
    model = Event
    name = 'esupa-check-all'


class SubscriptionList(EsupaListView):
    model = Subscription
    name = 'esupa-check-event'
    _event = None
    sort_dict = {
        'state': '-state',
        'sid': 'id',
        'pos': 'position',
    }

    @property
    def event(self) -> Event:
        if not self._event:
            try:
                self._event = Event.objects.get(slug=self.args[0])
            except Event.DoesNotExist:
                raise Http404
        return self._event

    def get_queryset(self):
        queryset = self.event.subscription_set
        sort = self.request.GET.get('sort')
        if sort == 'pos':
            queryset = queryset.filter(position__isnull=False)
        return queryset.order_by(self.sort_dict.get(sort, '-state'))

    def get_context_data(self, **kwargs):
        return super().get_context_data(event=self.event, **kwargs)


class TransactionList(EsupaListView):
    model = Transaction
    name = 'esupa-check-docs'
    _event = None
    _subscription = None

    @property
    def event(self) -> Event:
        if not self._event:
            self._event = self.subscription.event
        return self._event

    @property
    def subscription(self) -> Subscription:
        if not self._subscription:
            try:
                self._subscription = Subscription.objects.get(id=int(self.args[0]))
            except Subscription.DoesNotExist:
                raise Http404
            self._event = self._subscription.event
        return self._subscription

    def get_queryset(self):
        return self.subscription.transaction_set.order_by('-id')

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            event=self.event,
            sub=self.subscription,
            state=SubsState(),
            manual_transaction_form=ManualTransactionForm(self.subscription),
            **kwargs)

    def post(self, request: HttpRequest, sid: str):
        if 'action' in request.POST:
            tid, decision = request.POST.get('action').split()
            transaction = Transaction.objects.get(id=tid, subscription_id=int(sid))
            transaction.end(decision == 'yes')
            transaction.verifier = request.user
        else:
            form = ManualTransactionForm(request.POST)
            if form.is_valid():
                transaction = Transaction(subscription_id=int(sid))
                transaction.amount = form.cleaned_data['amount']
                transaction.created_at = form.cleaned_data['when']
                transaction.method = 1
                if request.FILES:
                    transaction.mimetype = request.FILES['attachment'].content_type or 'application/octet-stream'
                    transaction.document = request.FILES['attachment'].read()
                transaction.filled_at = transaction.created_at
                transaction.verifier = request.user
                transaction.notes = form.cleaned_data['notes']
                transaction.end(True)
            else:
                return self.get(request, sid)
        return prg_redirect(TransactionList.name, sid)
