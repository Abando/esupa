# coding=utf-8
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import SubscriptionForm, UploadForm
from .models import Event, Subscription, SubsState, Transaction
from .payment import Deposit, Processor
from .queue import QueueAgent


def get_event() -> Event:
    """Takes first Event set in the future."""
    queryset = Event.objects
    queryset = queryset.filter(starts_at__gt=timezone.now())
    queryset = queryset.order_by('starts_at')
    return queryset.first()


def get_subscription(event, user) -> Subscription:
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
    queue = QueueAgent(subscription)

    # redirect away if appropriate
    if action == 'pay_processor' and event.sales_open and queue.within_capacity:
        processor = Processor(subscription)
        return redirect(processor.start_and_go())
    elif state == SubsState.DENIED:
        raise PermissionDenied()

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
        if SubsState.NEW <= state < SubsState.WAITING:
            buttons.append(('edit', 'Editar'))
    else:
        buttons.append(('save', 'Salvar'))

    # perform appropriate saves if applicable
    if action == 'save' and form.is_valid() and SubsState.NEW <= state < SubsState.VERIFYING_PAY:
        form.copy_into(subscription)
        s = map(str.lower, (subscription.full_name, subscription.email, subscription.document, subscription.badge))
        b = tuple(map(str.lower, filter(bool, event.data_to_be_checked.splitlines())))
        acceptable = True not in (t in d for d in s for t in b)
        subscription.state = SubsState.ACCEPTABLE if acceptable else SubsState.VERIFYING_DATA
        subscription.save()  # action=save

    # deal with payment related stuff
    context['documents'] = subscription.transaction_set.filter(filled_at__isnull=False).values(
        'id', 'filled_at', 'ended_at', 'accepted')
    if subscription.id and (event.sales_open or subscription.waiting):
        deposit = Deposit(subscription)
        if deposit.expecting_file:
            context['upload_form'] = UploadForm()
        if action.startswith('pay'):
            subscription.position = queue.add()
            if not queue.within_capacity:
                subscription.waiting = False
            elif action == 'pay_deposit':
                if len(request.FILES):
                    deposit.got_file(request.FILES['upload'])
                else:
                    deposit.register_intent()
        if SubsState.ACCEPTABLE <= state < SubsState.VERIFYING_PAY and action != 'edit':
            if queue.within_capacity:
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
        raise Http404()
    if not request.user.is_staff and trans.subscription.user != request.user:
        raise PermissionDenied()
    response = HttpResponse(trans.document, mimetype='image')
    return response
