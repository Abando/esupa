# coding=utf-8
from django.core.exceptions import PermissionDenied


class Processor:
    def __init__(self, subscription):
        if not subscription.id:
            raise PermissionDenied('Payment without subscription.')
        self.subs = subscription
        self.url = None

    def create_transaction(self):
        self.url = '...'  # TODO


class Deposit:
    def __init__(self, subscription):
        pass

    def got_files(self, FILES):
        pass