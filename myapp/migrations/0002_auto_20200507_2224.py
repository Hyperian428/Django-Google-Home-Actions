# Generated by Django 2.2.6 on 2020-05-07 22:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='accessToken',
            field=models.CharField(default='0', max_length=30),
        ),
        migrations.AddField(
            model_name='account',
            name='intentId',
            field=models.CharField(default='0', max_length=10),
        ),
        migrations.AddField(
            model_name='account',
            name='intentRequestId',
            field=models.CharField(default='0', max_length=256),
        ),
    ]
