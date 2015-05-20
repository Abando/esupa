# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=20)),
                ('slug', models.SlugField(blank=True)),
                ('agreement_url', models.URLField(blank=True)),
                ('starts_at', models.DateTimeField()),
                ('min_age', models.IntegerField(default=0)),
                ('price', models.DecimalField(max_digits=7, decimal_places=2)),
                ('capacity', models.IntegerField()),
                ('subs_open', models.BooleanField(default=False)),
                ('subs_start_at', models.DateTimeField(null=True, blank=True)),
                ('sales_open', models.BooleanField(default=False)),
                ('sales_start_at', models.DateTimeField(null=True, blank=True)),
                ('deposit_info', models.TextField(blank=True)),
                ('payment_wait_hours', models.IntegerField(default=48)),
                ('data_to_be_checked', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Optional',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=20)),
                ('price', models.DecimalField(max_digits=7, decimal_places=2)),
            ],
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('state', models.SmallIntegerField(choices=[(0, 'Nova'), (11, 'Preenchida'), (33, 'Em fila para poder pagar'), (55, 'Aguardando pagamento'), (66, 'Verificando pagamento'), (88, 'Tripulante não pago'), (99, 'Confirmada'), (-1, 'Verificando dados'), (-9, 'Rejeitada')], default=0)),
                ('wait_until', models.DateTimeField(null=True, blank=True)),
                ('full_name', models.CharField(max_length=80)),
                ('document', models.CharField(max_length=30)),
                ('badge', models.CharField(max_length=30)),
                ('email', models.CharField(max_length=80)),
                ('phone', models.CharField(max_length=20)),
                ('born', models.DateField()),
                ('shirt_size', models.CharField(max_length=4)),
                ('blood', models.CharField(max_length=3)),
                ('health_insured', models.BooleanField(default=False)),
                ('contact', models.TextField(blank=True)),
                ('medication', models.TextField(blank=True)),
                ('agreed', models.BooleanField(default=False)),
                ('position', models.IntegerField(null=True, blank=True)),
                ('paid', models.BooleanField(default=False)),
                ('paid_at', models.DateTimeField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('payee', models.CharField(max_length=10, blank=True)),
                ('value', models.DecimalField(max_digits=7, decimal_places=2)),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('method', models.SmallIntegerField(choices=[(0, 'Em Mãos'), (1, 'Depósito'), (2, 'PagSeguro')], default=0)),
                ('remote_identifier', models.CharField(max_length=50, blank=True)),
                ('document', models.BinaryField(null=True)),
                ('filled_at', models.DateTimeField(null=True, blank=True)),
                ('accepted', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True)),
                ('ended_at', models.DateTimeField(null=True, blank=True)),
                ('subscription', models.ForeignKey(to='esupa.Subscription')),
                ('verifier', models.ForeignKey(to=settings.AUTH_USER_MODEL, blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='QueueContainer',
            fields=[
                ('event', models.OneToOneField(to='esupa.Event', serialize=False, primary_key=True)),
                ('data', models.TextField(default='[]')),
            ],
        ),
        migrations.AddField(
            model_name='subscription',
            name='event',
            field=models.ForeignKey(to='esupa.Event'),
        ),
        migrations.AddField(
            model_name='subscription',
            name='optionals',
            field=models.ManyToManyField(to='esupa.Optional', blank=True),
        ),
        migrations.AddField(
            model_name='subscription',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='optional',
            name='event',
            field=models.ForeignKey(to='esupa.Event'),
        ),
    ]
