# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('esupa', '0005_auto_20150721_0132'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='partial_payment_open',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='event',
            name='partial_payment_toggle',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='state',
            field=models.SmallIntegerField(choices=[(0, 'New'), (11, 'Filled'), (33, 'Queued for pay'), (55, 'Expecting payment'), (66, 'Verifying payment'), (77, 'Partially paid'), (88, 'Unpaid staff'), (99, 'Confirmed'), (-1, 'Checking data'), (-9, 'Rejected')], default=0),
        ),
    ]
