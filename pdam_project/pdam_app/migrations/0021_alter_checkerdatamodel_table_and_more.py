# Generated by Django 4.2.11 on 2024-07-19 01:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pdam_app', '0020_alter_maintenancerecordmodel_table_and_more'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='checkerdatamodel',
            table='pdam_checker_data',
        ),
        migrations.AlterModelTable(
            name='sensordatamodel',
            table='pdam_sensor_data',
        ),
    ]
