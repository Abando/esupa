from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.template import RequestContext, loader
from django.utils import timezone
from .forms import SubscriptionForm
from .models import Event, Subscription
from .payment import Processor, Deposit

def get_event():
	"""Takes first Event set in the future."""
	queryset = Event.objects
	queryset = queryset.filter(starts_at__gt = timezone.now())
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
	state = Subscription.state # UNCONFIRMED WAITING VERIFYING UNPAID_STAFF CONFIRMED
	action = request.POST.get('action')
	if request.method == 'POST' and action == 'save':
		form = SubscriptionForm(subscription, request.POST)
	elif subscription.id:
		form = SubscriptionForm(subscription, model_to_dict(subscription))
	else:
		form = SubscriptionForm(subscription)
	if form.is_valid() and action != 'edit':
		form.freeze()
		actions = []
		if state < Subscription.WAITING:
			actions.append(('edit', 'Editar'))
	else:
		actions = [('save', 'Salvar')]
	actions = (
		('edit',    'Editar',                      state < Subscription.WAITING),
		('pay',     'Pagar com Cartão',            state < Subscription.VERIFYING),
		('deposit', 'Pagar com Depósito Bancário', state < Subscription.VERIFYING))
	else:
	actions = filter(lambda x:x[2], actions)
	context = { 'subscription_form': form, 'actions': actions }
	if action == 'pay':
		processor = Processor(subscription)
		processor.create_transaction()
		return redirect(processor.url)
	#context['debug'] = repr(request.POST.get('action'))
	return render(request, 'esupa/form.html', context)

@login_required
def see_transaction_document(request, tid):
	# TODO: Add ETag generation & verification… maybe… eventually…
	trans = Transaction.objects.get(id=tid)
	if trans == None:
		raise Http404()
	image = trans.document
	if not image:
		raise Http404()
	if not request.user.is_staff and trans.subscription.user != request.user:
		raise PermissionDenied()
	response = HttpResponse(image, mimetype='image')
	return response
