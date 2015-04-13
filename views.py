from django.http import HttpResponse
from django.shortcuts import render
from django.template import RequestContext, loader

def index(request):
	return edit(request)

def edit(request):
	template = loader.get_template('inev/edit.html')
	context = RequestContext(request, {
		'errors': {},
		'inputs': {},
		'event': {},
		'optionals': [],
	})
	return HttpResponse(template.render(context))

