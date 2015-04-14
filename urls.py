from django.conf.urls import url
from . import views

urlpatterns = [
	url(r'^$', views.index, name='index'),
	url(r'edit$', views.edit, name='edit'),
	url(r'view$', views.view, name='view'),
]
