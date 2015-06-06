# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('esupa', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='event',
            old_name='sales_start_at',
            new_name='sales_toggle',
        ),
        migrations.RenameField(
            model_name='event',
            old_name='subs_start_at',
            new_name='subs_toggle',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='paid',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='paid_at',
        ),
    ]
