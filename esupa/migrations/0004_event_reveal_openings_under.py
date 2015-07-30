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
        ('esupa', '0003_auto_20150612_2244'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='slug',
            field=models.SlugField(validators=[slug_blacklist_validator_loader()], unique=True),
        ),
        migrations.AddField(
            model_name='event',
            name='reveal_openings_under',
            field=models.IntegerField(default=0, blank=True),
        ),
    ]
