# Generated by Django 4.2.11 on 2024-07-19 01:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pdam_app', '0016_maintenancerecordmode'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='MaintenanceRecordMode',
            new_name='MaintenanceRecordModel',
        ),
    ]