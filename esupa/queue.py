# -*- coding: utf-8 -*-
#
# Copyright 2015, Ekevoo.com.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.
#
"""
Very simple implementation designed for single server, single process, few users.

May scalability ever become an issue, replace this with something like Celery and
RabbitMQ. Let's not reinvent the wheel too much, shall we?
"""
from json import dumps, loads
from logging import getLogger
from threading import Lock

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.timezone import now

from .notify import BatchNotifier
from .models import Event, QueueContainer, Subscription, SubsState

log = getLogger(__name__)


class LockDict(dict):
    def __init__(self, lock=Lock, **kwargs):
        self.lock = lock
        self.outer = lock()
        super().__init__(**kwargs)

    def __getitem__(self, key):
        with self.outer:
            if key not in self:
                self[key] = self.lock()
            return super().__getitem__(key)


_lock = LockDict()


class QueueAgent:
    """
    This agent will atomically act upon the event queue on behalf of one subscription.

    It caches some stuff, so don't keep it for longer than one HTTP request.
    """

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
        with _lock[self.eid]:
            qc, created = QueueContainer.objects.get_or_create(event_id=self.eid)
            queue = [] if created else loads(qc.data)
            return operation(queue, self.s.id)

    def _atomic_db_write(self, operation):
        with _lock[self.eid]:
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


def _update_all_subscriptions(event, notify):
    """Oh boy, this will take a while. But it has to be done sometimes."""
    qc, created = QueueContainer.objects.get_or_create(event=event)
    if created:
        return
    queue = loads(qc.data)
    position = 0
    for sid in list(queue):  # iterate over a copy
        try:
            subscription = Subscription.objects.get(id=sid)
        except ObjectDoesNotExist:
            _remove(queue, sid)
            subscription.wait_until = None
            subscription.position = None
            subscription.save()
        if subscription.state == SubsState.EXPECTING_PAY and not subscription.waiting:
            _remove(queue, sid)
            subscription.state = SubsState.ACCEPTABLE
            subscription.wait_until = None
            subscription.position = None
            subscription.save()
            notify.expired(subscription)
        elif subscription.state == SubsState.QUEUED_FOR_PAY and position < event.capacity:
            subscription.state = SubsState.EXPECTING_PAY
            subscription.waiting = True
            subscription.position = _add(queue, sid)
            subscription.save()
            notify.can_pay(subscription)
            position += 1
        else:
            if subscription.position != position:
                subscription.position = position
                subscription.save()
            position += 1
    subscriptions = Subscription.objects.filter(event=event)
    subscriptions.exclude(id__in=queue).update(position=None)
    qc.data = dumps(queue)
    qc.save()


def cron():
    for event in Event.objects.filter(starts_at__gt=now()).iterable():
        notify = BatchNotifier()
        with _lock[event.id], transaction.atomic():
            _update_all_subscriptions(event, notify)
        notify.send_notifications()
