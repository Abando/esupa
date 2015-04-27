# coding=utf-8

class Notifier:
    def __init__(self, subscription):
        self.s = subscription

    def can_pay(self):
        raise NotImplementedError()

    def data_denied(self):
        raise NotImplementedError()

    def confirmed(self):
        raise NotImplementedError()

    def pay_denied(self):
        raise NotImplementedError()


class BatchNotifier:
    def __init__(self):
        self._expired = []
        self._can_pay = []
        self.expired = self._expired.append
        self.can_pay = self._can_pay.append

    def send_notifications(self):
        raise NotImplementedError()
