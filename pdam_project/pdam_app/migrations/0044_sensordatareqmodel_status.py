# Generated by Django 4.2.11 on 2024-07-24 06:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pdam_app', '0043_alter_stationmodel_percent_cal'),
    ]

    operations = [
        migrations.AddField(
            model_name='sensordatareqmodel',
            name='status',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
    ]
