from django.contrib.auth.decorators import login_required
from django.forms.models import model_to_dict
from django.http import HttpResponse
from django.shortcuts import render
from django.template import RequestContext, loader
from django.utils import timezone
from .forms import SubscriptionForm
from .models import Event, Subscription

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
	if result is None:
		result = Subscription(event = event, user = user)
	return result

@login_required
def index(request, cmd=None):
	event = get_event()
	subscription = get_subscription(event, request.user)
	if request.method == 'POST':
		form = SubscriptionForm(subscription, request.POST)
	elif subscription.id:
		form = SubscriptionForm(subscription, model_to_dict(subscription))
	else:
		form = SubscriptionForm(subscription)
	if form.is_valid() and request.POST.get('action') is not 'edit':
		form.freeze()
	actions = (
		('save', 'Salvar'),
		('edit', 'Editar'),
		('pay', 'Pagar com Cartão'),
		('deposit', 'Pagar com Depósito Bancário'))
	context = { 'subscription_form': form, 'actions': actions}
	#context['debug'] = repr(request.POST.get('action'))
	return render(request, 'esupa/form.html', context)
