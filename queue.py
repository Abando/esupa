# coding=utf-8
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from json import dumps, loads
from threading import Lock
from .models import QueueContainer, Subscription, Event

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


def _update_all_subscriptions(event):
    """Oh boy, this will take a while. But it has to be done sometimes."""
    qc, created = QueueContainer.objects.get_or_create(event=event)
    if created:
        return
    queue = loads(qc.data)
    for sid in list(queue): # iterate over a copy
        try:
            s = Subscription.objects.get(id=sid)
        except ObjectDoesNotExist:
            _remove(queue, sid)
        assert isinstance(s, Subscription)
        if not s.waiting:
            _remove(queue, sid)
            s.transaction_set.filter(ended_at__isnull=True).update(ended_at=datetime.now())
        # TODO: Notify?
    subscriptions = Subscription.objects.filter(event=event)
    subscriptions.exclude(id__in=queue).update(position=None)
    count = 0
    for sid in loads(qc.data):
        count += subscriptions.filter(id=sid).update(position=count)


def cron():
    for e in Event.objects.filter(starts_at__gt=datetime.now()).iterable():
        with _lock, transaction.atomic():
            _update_all_subscriptions(e)