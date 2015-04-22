# coding=utf-8
from django.db import transaction
from json import dumps, loads
from threading import Lock
from .models import QueueContainer, Subscription

"""
Very simple implementation designed for single server, single process, few users.

May scalability ever become an issue, replace this with something like Celery and
RabbitMQ. Let's not reinvent the wheel too much, shall we?
"""

_lock = Lock()  # this could be event specific, but for now let's keep it global


class QueueAgent:
    """This agent will atomically act upon the event queue on behalf of one subscription. It caches some stuff, so
    don't keep it for long."""
    def __init__(self, subscription):
        self.s = subscription
        self.eid = subscription.event_id
        self.pos = None

    @property
    def within_capacity(self) -> bool:
        """Checks if subscription is trying to enter/use the queue under capacity."""
        if self.pos is None:
            self.pos = self._atomic_db_read(_ghost_add)
        return self.pos < self.s.event.capacity

    def add(self) -> int:
        """Adds it to the queue if not already there; returns position."""
        self.pos = self._atomic_db_write(_add)
        return self.pos

    def remove(self):
        """Removes from queue if not there."""
        self.pos = None
        return self._atomic_db_write(_remove)

    def _atomic_db_read(self, operation):
        with _lock:
            qc, created = QueueContainer.objects.get_or_create(event_id=self.eid)
            queue = [] if created else loads(qc.data)
            return operation(queue, self.s.id)

    def _atomic_db_write(self, operation):
        with _lock:
            qc, created = QueueContainer.objects.get_or_create(event_id=self.eid)
            queue = [] if created else loads(qc.data)
            result = operation(queue, self.s.id)
            qc.data = dumps(queue)
            qc.save()  # assuming autocommit is on
            return result


def _ghost_add(queue, sid):
    try:
        return queue.index(sid)
    except ValueError:
        return len(queue)


def _add(queue, sid):
    try:
        return queue.index(sid)
    except ValueError:
        queue.append(sid)
        return len(queue) - 1


def _remove(queue, sid):
    try:
        queue.remove(sid)
    except ValueError:
        pass


def update_all_subscriptions(event_id):
    """Oh boy, this will take a while. But it has to be done sometimes."""
    with _lock, transaction.atomic():
        qc, created = QueueContainer.objects.get_or_create(event_id=event_id)
        if created:
            return
        queue = loads(qc.data)
        subscriptions = Subscription.objects.filter(event_id=event_id)
        subscriptions.exclude(id__in=queue).update(position=None)
        count = 0
        for sid in loads(qc.data):
            count += subscriptions.filter(id=sid).update(position=count)
