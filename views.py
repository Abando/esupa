from django.contrib.auth.decorators import login_required
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

def index(request, cmd=None):
	# TODO: make view mode
	event = get_event()
	subscription = get_subscription(event, request.user)
	form = SubscriptionForm(subscription)
	if cmd == 'view': form.freeze()
	context = {'form': form}
	return render(request, 'esupa/form.html', context)

index = login_required(index)
view = lambda req:index(req, 'view')
edit = lambda req:index(req, 'edit')
