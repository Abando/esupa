# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def slug_blacklist_validator_loader():
    try:
        from ..models import slug_blacklist_validator
    except ImportError:
        slug_blacklist_validator = lambda target: None
    return slug_blacklist_validator


class Migration(migrations.Migration):

    dependencies = [
        ('esupa', '0002_transaction_mimetype'),
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
        migrations.AlterField(
            model_name='event',
            name='slug',
            field=models.SlugField(validators=[slug_blacklist_validator_loader()]),
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='paid',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='paid_at',
        ),
        migrations.AlterField(
            model_name='subscription',
            name='state',
            field=models.SmallIntegerField(default=0, choices=[(0, 'Nova'), (11, 'Preenchida'), (33, 'Em fila para poder pagar'), (55, 'Aguardando pagamento'), (66, 'Verificando pagamento'), (77, 'Parcialmente paga'), (88, 'Tripulante não pago'), (99, 'Confirmada'), (-1, 'Verificando dados'), (-9, 'Rejeitada')]),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='method',
            field=models.SmallIntegerField(default=0),
        ),
    ]
