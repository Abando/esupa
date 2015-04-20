from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.template import RequestContext, loader
from django.utils import timezone
from .forms import SubscriptionForm
from .models import Event, Subscription, SubsState
from .payment import Processor, Deposit

def get_event():
	"""Takes first Event set in the future."""
	queryset = Event.objects
	queryset = queryset.filter(starts_at__gt = timezone.now(), subs_open = True)
	queryset = queryset.order_by('starts_at')
	return queryset.first()

def get_subscription(event, user):
	"""Takes existing subscription if available, creates a new one otherwise."""
	queryset = Subscription.objects
	queryset = queryset.filter(event = event, user = user)
	result = queryset.first()
	if result == None:
		result = Subscription(event = event, user = user)
	return result

@login_required
def index(request):
	event = get_event()
	subscription = get_subscription(event, request.user)
	action = request.POST.get('action', default='view')
	if action == 'pay_processor' and subscription.can_enter_queue():
		processor = Processor(subscription)
		processor.create_transaction()
		return redirect(processor.url)
	state = subscription.state
	context = {}
	if request.method == 'POST' and action == 'save':
		form = SubscriptionForm(subscription, request.POST)
	elif subscription.id:
		form = SubscriptionForm(subscription, model_to_dict(subscription))
	else:
		form = SubscriptionForm(subscription)
	context['subscription_form'] = form
	context['actions'] = actions = []
	if form.is_valid() and action != 'edit':
		form.freeze()
		if state < SubsState.WAITING:
			actions.append(('edit', 'Editar'))
	else:
		actions.append(('save', 'Salvar'))
	if action == 'save':
		for field in form.fields:
			subscription.fields[field] = form.fields[field]
		repr(subscription)
	# TODO: retrieve transactions, potentially update state depending on action
	if event.sales_open and SubsState.ACCEPTABLE <= state < SubsState.VERIFYING:
		if event.can_enter_queue():
			actions.append(('pay_deposit',   'Pagar com Depósito Bancário'))
			actions.append(('pay_processor', 'Pagar com PagSeguro'))
		else:
			actions.append(('pay_none',      'Entrar na fila de pagamento'))
	return render(request, 'esupa/form.html', context)

@login_required
def see_transaction_document(request, tid):
	# TODO: Add ETag generation & verification… maybe… eventually…
	trans = Transaction.objects.get(id=tid)
	if trans == None or not trans.document:
		raise Http404()
	if not request.user.is_staff and trans.subscription.user != request.user:
		raise PermissionDenied()
	response = HttpResponse(trans.document, mimetype='image')
	return response
