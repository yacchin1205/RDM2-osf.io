# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osf', '0226_ensure_schema_and_reports'),
    ]

    operations = [
        migrations.AlterField(
            model_name='FileLog',
            name='path',
            field=models.TextField(null=True),
        ),
    ]
