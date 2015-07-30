# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def discover_mimetype(apps, _):
    try:
        # sudo -H pip3 install python-magic
        from magic import Magic
    except ImportError:
        Magic = None

    guess_mime = Magic(mime=True).from_buffer if Magic else lambda _: 'application/x-octet-stream'

    t = apps.get_model('esupa', 'Transaction')
    for transaction in t.objects.all():
        if transaction.document:
            transaction.mimetype = guess_mime(transaction.document)
            transaction.save()
        print('Transaction#%d detected mimetype is %s.' % (transaction.id, transaction.mimetype))


class Migration(migrations.Migration):
    dependencies = [
        ('esupa', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='mimetype',
            field=models.CharField(max_length=255, blank=True),
        ),
        migrations.RunPython(discover_mimetype),
    ]
