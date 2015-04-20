from django.core.exceptions import PermissionDenied
from .models import Event, Subscription

class Processor:
	def __init__(self, subscription):
		if not subscription.id:
			raise PermissionDenied('Payment without subscription.')
		self.subs = subscription
		self.url = None
	def create_transaction(self):
		self.url = '...' # TODO

class Deposit:
	pass
