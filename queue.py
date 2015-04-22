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

_lock = Lock()  # this could be event specific, but for now let's keep it simple


def within_capacity(subscription):
    """Checks if subscription is trying to enter/use the queue under capacity."""

    def operation(queue, sid, capacity):
        if len(queue) < capacity:
            return True
        try:
            pos = queue.index(sid)
            return pos < capacity
        except ValueError:
            return False

    event = subscription.event
    return _atomic_db_read(operation, event.id, subscription.id, event.capacity)


def add(subscription):
    """Adds it to the queue if not already there; returns position."""

    def operation(queue, sid):
        try:
            return queue.index(sid)
        except ValueError:
            queue.append(sid)
            return len(queue) - 1

    return _atomic_db_write(operation, subscription.event_id, subscription.id)


def remove(subscription):
    """Removes from queue if not there, returns whether it was."""

    def operation(queue, sid):
        try:
            queue.remove(sid)
            return True
        except ValueError:
            return False

    return _atomic_db_write(operation, subscription.event_id, subscription.id)


get_snapshot = lambda event_id: _atomic_db_read(lambda q: q, event_id)


def _atomic_db_read(operation, eid, *args, **kwargs):
    with _lock:
        db, created = QueueContainer.objects.get_or_create(event_id=eid)
        queue = [] if created else loads(db.data)
        return operation(queue, *args, **kwargs)


def _atomic_db_write(operation, eid, *args, **kwargs):
    with _lock:
        db, created = QueueContainer.objects.get_or_create(event_id=eid)
        queue = [] if created else loads(db.data)
        result = operation(queue, *args, **kwargs)
        db.data = dumps(queue)
        db.save()  # assuming autocommit is on
        return result


def update_all_subscriptions(event_id):
    """Oh boy, this will take a while. But it has to be done sometimes."""
    with _lock, transaction.atomic():
        db, created = QueueContainer.objects.get_or_create(event_id=event_id)
        subscriptions = Subscription.objects.filter(event_id=event_id)
        subscriptions.update(position=None)
        if created:
            return
        count = 0
        for sid in loads(db.data):
            count += subscriptions.filter(id=sid).update(position=count)
