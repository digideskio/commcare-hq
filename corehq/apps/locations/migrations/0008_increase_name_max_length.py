# -*- coding: utf-8 -*-
# Generated by Django 1.9.12 on 2017-03-01 16:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0007_add_blank_true'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sqllocation',
            name='name',
            field=models.CharField(max_length=255, null=True),
        ),
    ]