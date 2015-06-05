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
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=20)),
                ('slug', models.SlugField(blank=True)),
                ('agreement_url', models.URLField(blank=True)),
                ('starts_at', models.DateTimeField()),
                ('min_age', models.IntegerField(default=0)),
                ('price', models.DecimalField(decimal_places=2, max_digits=7)),
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
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=20)),
                ('price', models.DecimalField(decimal_places=2, max_digits=7)),
            ],
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('state', models.SmallIntegerField(default=0, choices=[(0, 'Nova'), (11, 'Preenchida'), (33, 'Em fila para poder pagar'), (55, 'Aguardando pagamento'), (66, 'Verificando pagamento'), (88, 'Tripulante não pago'), (99, 'Confirmada'), (-1, 'Verificando dados'), (-9, 'Rejeitada')])),
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
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('payee', models.CharField(blank=True, max_length=10)),
                ('value', models.DecimalField(decimal_places=2, max_digits=7)),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('method', models.SmallIntegerField(default=0)),
                ('remote_identifier', models.CharField(blank=True, max_length=50)),
                ('mimetype', models.CharField(blank=True, max_length=255)),
                ('document', models.BinaryField(null=True)),
                ('filled_at', models.DateTimeField(null=True, blank=True)),
                ('accepted', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True)),
                ('ended_at', models.DateTimeField(null=True, blank=True)),
                ('subscription', models.ForeignKey(to='esupa.Subscription')),
                ('verifier', models.ForeignKey(null=True, blank=True, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='QueueContainer',
            fields=[
                ('event', models.OneToOneField(to='esupa.Event', primary_key=True, serialize=False)),
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
            field=models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='optional',
            name='event',
            field=models.ForeignKey(to='esupa.Event'),
        ),
    ]
