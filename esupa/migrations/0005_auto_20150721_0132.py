# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('esupa', '0004_event_reveal_openings_under'),
    ]

    operations = [
        migrations.RenameField(
            model_name='transaction',
            old_name='value',
            new_name='amount',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='payee',
        ),
    ]
