from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.template import RequestContext, loader
from django.utils import timezone
from .models import Event, Subscription

def get_event():
	"""Takes first Event set in the future."""
	queryset = Event.objects
	queryset = queryset.filter(starts_at__gt = timezone.now())
	queryset = queryset.order_by('starts_at')
	return queryset.first()

def get_subscription(user):
	"""Takes existing subscription if available, creates a new one otherwise."""
	event = get_event()
	queryset = Subscription.objects
	queryset = queryset.filter(event = event, user = user)
	result = queryset.first()
	if result is None:
		result = Subscription(event = event, user = user)
	return result

def index(request):
	return edit(request)

def edit(request):
	context = {
		'errors': {},
		'inputs': get_subscription(request.user),
		'event': get_event(),
		'optionals': [],
	}
	return render(request, 'inev/edit.html', context)

def view(request):
	context = {
		'inputs': {},
		'event': get_event(),
		'optionals': [],
	}
	return render(request, 'inev/view.html', context)

edit = login_required(edit)
view = login_required(view)
