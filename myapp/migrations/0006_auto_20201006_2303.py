# Generated by Django 2.2.6 on 2020-10-06 23:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0005_auto_20200828_0008'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='intentId',
        ),
        migrations.RemoveField(
            model_name='account',
            name='intentRequestId',
        ),
    ]
