# coding=utf-8
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseForbidden, Http404
from django.shortcuts import redirect, render

from .forms import SubscriptionForm, UploadForm
from .models import Event, Subscription, SubsState, Transaction
from .notify import Notifier
from .payment import Deposit, Processor
from .queue import QueueAgent, cron


def get_event(slug=None) -> Event:
    """Takes given event or first set in the future."""
    if slug:
        try:
            return Event.objects.get(slug=slug)
        except ObjectDoesNotExist:
            raise Http404()
    else:
        e = Event.objects.filter(starts_at__gt=datetime.now()).order_by('starts_at').first()
        if e:
            return e
        else:
            raise Http404()


def get_subscription(event, user) -> Subscription:
    """Takes existing subscription if available, creates a new one otherwise."""
    queryset = Subscription.objects
    queryset = queryset.filter(event=event, user=user)
    result = queryset.first()
    if result is None:
        result = Subscription(event=event, user=user)
    return result


@login_required
def view_subscribe(request, eslug=None):
    event = get_event(eslug)
    subscription = get_subscription(event, request.user)
    action = request.POST.get('action', default='view')
    state = subscription.state
    queue = QueueAgent(subscription)

    # redirect away if appropriate
    if action == 'pay_processor' and event.sales_open and queue.within_capacity:
        return redirect(Processor.get(subscription).generate_transaction_url())
    elif state == SubsState.DENIED:
        return HttpResponseForbidden()

    # display subscription information no matter what
    if request.method == 'POST' and action == 'save':
        form = SubscriptionForm(subscription, request.POST)
    elif subscription.id:
        form = SubscriptionForm(subscription, model_to_dict(subscription))
    else:
        form = SubscriptionForm(subscription)
        form.email = request.user.email
    buttons = []
    context = {'subscription_form': form, 'actions': buttons}
    if not event.subs_open:
        form.freeze()
    elif form.is_valid() and action != 'edit':
        form.freeze()
        if SubsState.NEW <= state <= SubsState.QUEUED_FOR_PAY:
            buttons.append(('edit', 'Editar'))
    else:
        buttons.append(('save', 'Salvar'))

    # perform appropriate saves if applicable
    if action == 'save' and form.is_valid() and SubsState.NEW <= state <= SubsState.QUEUED_FOR_PAY:
        form.copy_into(subscription)
        s = map(str.lower, (subscription.full_name, subscription.email, subscription.document, subscription.badge))
        b = tuple(map(str.lower, filter(bool, event.data_to_be_checked.splitlines())))
        acceptable = True not in (t in d for d in s for t in b)
        subscription.state = SubsState.ACCEPTABLE if acceptable else SubsState.VERIFYING_DATA
        subscription.save()  # action=save

    # deal with payment related stuff
    context['documents'] = subscription.transaction_set.filter(filled_at__isnull=False).values(
        'id', 'filled_at', 'ended_at', 'accepted')
    if SubsState.ACCEPTABLE <= state <= SubsState.VERIFYING_PAY and (event.sales_open or subscription.waiting):
        deposit = Deposit(subscription)
        if action.startswith('pay'):
            subscription.position = queue.add()
            subscription.waiting = queue.within_capacity
            subscription.raise_state(SubsState.QUEUED_FOR_PAY if subscription.waiting else SubsState.EXPECTING_PAY)
            if len(request.FILES):
                deposit.got_file(request.FILES['upload'])
                subscription.raise_state(SubsState.VERIFYING_PAY)
            elif action == 'pay_deposit':
                deposit.register_intent()
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
    return render(request, 'esupa/form.html', context)


@login_required
def view_transaction_document(request, tid):
    # TODO: Add ETag generation & verification… maybe… eventually…
    trans = Transaction.objects.get(id=tid)
    if trans is None or not trans.document:
        return HttpResponseNotFound()
    if not request.user.is_staff and trans.subscription.user != request.user:
        return HttpResponseForbidden()
    response = HttpResponse(trans.document, mimetype='image')
    return response


def view_cron(_, secret):
    if secret != settings.ESUPA_CRON_SECRET:
        return HttpResponseBadRequest()
    cron()


def view_processor(request, slug):
    return Processor.view(slug, request)


@login_required
def view_verify(request):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    if request.method == 'POST':
        sid, acceptable = request.POST['action'].split()
        acceptable = acceptable == 'ok'
        subscription = Subscription.objects.get(id=int(sid))
        notify = Notifier(subscription)
        if subscription.state == SubsState.VERIFYING_DATA:
            if acceptable:
                subscription.state = SubsState.ACCEPTABLE
                subscription.save()
                notify.can_pay()
            else:
                subscription.state = SubsState.DENIED
                subscription.save()
                notify.data_denied()
        elif subscription.state == SubsState.VERIFYING_PAY:
            Deposit(subscription).accept(acceptable)
            if acceptable:
                subscription.state = SubsState.CONFIRMED
                subscription.wait_until = None
                subscription.save()
                notify.confirmed()
            else:
                subscription.state = SubsState.ACCEPTABLE
                subscription.wait_until = None
                subscription.position = None
                subscription.save()
                QueueAgent(subscription).remove()
                notify.pay_denied()
        else:
            return HttpResponseBadRequest('Invalid attempt to %s subscription %d (%s)' % (
                'accept' if acceptable else 'reject', sid, subscription.badge))
    context = {
        'VERIFYING_PAY': SubsState.VERIFYING_PAY,
        'VERIFYING_DATA': SubsState.VERIFYING_DATA,
        'states': SubsState.choices,
        'events': Event.objects,
        'subscriptions': Subscription.objects.filter(state__in=[SubsState.VERIFYING_DATA, SubsState.VERIFYING_PAY]),
    }
    return render(request, 'esupa/verify.html', context)


@login_required
def view_verify_event(request, eid):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    event = Event.objects.get(id=eid)
    return HttpResponse(str(event))
