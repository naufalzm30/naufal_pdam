# Generated by Django 4.2.11 on 2024-08-05 02:01

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('pdam_app', '0053_stationconfigurationmodel_hide_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='stationmodel',
            name='station_serial_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, verbose_name='uid'),
        ),
    ]