# coding=utf-8
from logging import getLogger

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, SuspiciousOperation
from django.http import HttpResponse, Http404, HttpRequest, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

from .forms import SubscriptionForm, UploadForm
from .models import Event, Subscription, SubsState, Transaction
from .notify import Notifier
from .payment import Deposit, Processor
from .queue import QueueAgent, cron

log = getLogger(__name__)


def get_event(slug=None) -> Event:
    """Takes given event or first set in the future."""
    if slug:
        try:
            return Event.objects.get(slug=slug)
        except ObjectDoesNotExist:
            raise Http404("No such event.")
    else:
        e = Event.objects.filter(starts_at__gt=now()).order_by('starts_at').first()
        if e:
            return e
        else:
            raise Http404("No default event.")


def get_subscription(event: Event, user: User) -> Subscription:
    """Takes existing subscription if available, creates a new one otherwise."""
    queryset = Subscription.objects
    queryset = queryset.filter(event=event, user=user)
    result = queryset.first()
    if result is None:
        result = Subscription(event=event, user=user)
    return result


@login_required
def view_subscribe(request: HttpRequest, eslug=None) -> HttpResponse:
    event = get_event(eslug)
    subscription = get_subscription(event, request.user)
    action = request.POST.get('action', default='view')
    state = subscription.state
    queue = QueueAgent(subscription)

    # redirect away if appropriate
    if action == 'pay_processor' and event.sales_open and queue.within_capacity:
        return redirect(Processor.get(subscription).generate_transaction_url())
    elif state == SubsState.DENIED:
        raise PermissionDenied

    # display subscription information
    if not subscription.id:
        subscription.email = subscription.user.email
    formdata = request.POST if request.method == 'POST' and action == 'save' else None
    form = SubscriptionForm(data=formdata, instance=subscription)
    buttons = []
    context = {
        'subscription_form': form,
        'actions': buttons,
        'event': event,
        'subscription': subscription,
    }
    if not event.subs_open:
        form.freeze()
    elif (action == 'view' and not subscription.id) or (action == 'edit') or (action == 'save' and form.errors):
        buttons.append(('save', 'Salvar'))
    else:
        form.freeze()
        if SubsState.NEW <= state <= SubsState.QUEUED_FOR_PAY:
            buttons.append(('edit', 'Editar'))

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
    if SubsState.ACCEPTABLE <= state <= SubsState.VERIFYING_PAY and (event.sales_open or subscription.waiting):
        deposit = Deposit(subscription)
        if action.startswith('pay'):
            subscription.position = queue.add()
            subscription.waiting = queue.within_capacity
            subscription.raise_state(SubsState.QUEUED_FOR_PAY if subscription.waiting else SubsState.EXPECTING_PAY)
            if len(request.FILES):
                deposit.got_file(request.FILES['upload'])
                subscription.raise_state(SubsState.VERIFYING_PAY)
                Notifier(subscription).staffer_action_required()
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
    context['state'] = SubsState(subscription.state)
    return render(request, 'esupa/form.html', context)


@login_required
def view_transaction_document(request: HttpRequest, tid) -> HttpResponse:
    # Add ETag generation & verification… maybe… eventually…
    trans = Transaction.objects.get(id=tid)
    if trans is None or not trans.document:
        raise Http404("No such document.")
    if not request.user.is_staff and trans.subscription.user != request.user:
        return PermissionDenied
    response = HttpResponse(trans.document, content_type='image/jpeg')
    return response


def view_cron(_, secret) -> HttpResponse:
    if secret != settings.ESUPA_CRON_SECRET:
        raise SuspiciousOperation
    cron()
    return HttpResponse()  # no response


@csrf_exempt
def view_processor(request: HttpRequest, slug) -> HttpResponse:
    return Processor.dispatch_view(slug, request) or HttpResponse()


@login_required  # TODO: @permission_required(???)
def view_verify(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        raise PermissionDenied
    return render(request, 'esupa/verify.html', {'events': Event.objects})


@login_required
def view_verify_event(request: HttpRequest, eid) -> HttpResponse:
    if not request.user.is_staff:
        raise PermissionDenied
    event = Event.objects.get(id=int(eid))
    subscriptions = event.subscription_set.order_by('-state').all()
    context = {'event': event, 'subscriptions': subscriptions, 'state': SubsState()}
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
        elif subscription.state == SubsState.VERIFYING_PAY:
            Deposit(transaction).accept(acceptable)
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
            return HttpResponseBadRequest('Invalid attempt to %s %s=%d (%s) because subscription state is %s' % (
                'accept' if acceptable else 'reject', what, oid, subscription.badge, SubsState(subscription.state)))
    return render(request, 'esupa/event-verify.html', context)
