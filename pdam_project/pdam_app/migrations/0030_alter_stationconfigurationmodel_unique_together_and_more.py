# Generated by Django 4.2.11 on 2024-07-19 06:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pdam_app', '0029_alter_stationconfigurationmodel_modified_at'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='stationconfigurationmodel',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='stationconfigurationmodel',
            constraint=models.UniqueConstraint(fields=('station', 'channel', 'sensor_type'), name='unique_station_channel_sensor_type'),
        ),
    ]
