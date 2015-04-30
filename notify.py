# coding=utf-8
from logging import getLogger

logger = getLogger(__name__)


class Notifier:
    def __init__(self, subscription):
        self.s = subscription

    def can_pay(self):
        """This can happen in two cases, (1) esupa staff data verify accepted, or (2) the queue moved."""
        raise NotImplementedError()

    def data_denied(self):
        """Esupa staff data verify failed."""
        raise NotImplementedError()

    def confirmed(self):
        """Pay has been accepted."""
        raise NotImplementedError()

    def pay_denied(self):
        """Pay has been denied."""
        raise NotImplementedError()

    def staffer_action_required(self):
        """Sent to staffers, telling them that they're supposed to verify some data."""
        raise NotImplementedError()


class BatchNotifier:
    def __init__(self):
        self._expired = []
        self._can_pay = []
        self.expired = self._expired.append
        self.can_pay = self._can_pay.append

    def send_notifications(self):
        raise NotImplementedError()
