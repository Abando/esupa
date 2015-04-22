# coding=utf-8
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import SubscriptionForm
from .models import Event, Subscription, SubsState, Transaction
from .payment import Processor
from . import queue


def get_event():
    """Takes first Event set in the future."""
    queryset = Event.objects
    queryset = queryset.filter(starts_at__gt=timezone.now(), subs_open=True)
    queryset = queryset.order_by('starts_at')
    return queryset.first()


def get_subscription(event, user):
    """Takes existing subscription if available, creates a new one otherwise."""
    queryset = Subscription.objects
    queryset = queryset.filter(event=event, user=user)
    result = queryset.first()
    if result is None:
        result = Subscription(event=event, user=user)
    return result


@login_required
def index(request):
    event = get_event()
    subscription = get_subscription(event, request.user)
    action = request.POST.get('action', default='view')
    state = subscription.state
    within_capacity = queue.Cached(lambda:queue.within_capacity(subscription))

    # first order of business, redirect away if appropriate
    if action == 'pay_processor' and event.sales_open and within_capacity():
        processor = Processor(subscription)
        processor.create_transaction()
        return redirect(processor.url)
    elif state == SubsState.DENIED:
        raise PermissionDenied()

    # second order of business: display subscription information no matter what
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
        if SubsState.NEW <= state < SubsState.WAITING:
            buttons.append(('edit', 'Editar'))
    else:
        buttons.append(('save', 'Salvar'))

    # third order of business: perform appropriate saves if applicable
    if action == 'save' and form.is_valid() and SubsState.NEW <= state < SubsState.VERIFYING_PAY:
        form.copy_into(subscription)
        s = map(str.lower, (subscription.full_name, subscription.email, subscription.document, subscription.badge))
        b = tuple(map(str.lower, filter(bool, event.data_to_be_checked.splitlines())))
        acceptable = True not in (t in d for d in s for t in b)
        subscription.state = SubsState.ACCEPTABLE if acceptable else SubsState.VERIFYING_DATA
        subscription.save()
    if action.startswith('pay') and event.sales_open:
        if not within_capacity():
            position = queue.add(subscription)
            context['debug'] = 'Posição %d' % position  # FIXME
    if event.sales_open and SubsState.ACCEPTABLE <= state < SubsState.VERIFYING_PAY:
        if within_capacity():
            buttons.append(('pay_deposit', 'Pagar com Depósito Bancário'))
            buttons.append(('pay_processor', 'Pagar com PagSeguro'))
        else:
            buttons.append(('pay_none', 'Entrar na fila de pagamento'))
    return render(request, 'esupa/form.html', context)


@login_required
def see_transaction_document(request, tid):
    # TODO: Add ETag generation & verification… maybe… eventually…
    trans = Transaction.objects.get(id=tid)
    if trans is None or not trans.document:
        raise Http404()
    if not request.user.is_staff and trans.subscription.user != request.user:
        raise PermissionDenied()
    response = HttpResponse(trans.document, mimetype='image')
    return response
