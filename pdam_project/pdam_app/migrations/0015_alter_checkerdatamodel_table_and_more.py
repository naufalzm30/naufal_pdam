# Generated by Django 4.2.11 on 2024-07-17 03:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pdam_app', '0014_rename_modifiedrecord_modifiedrecordmodel'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='checkerdatamodel',
            table='pdam_checkerdata',
        ),
        migrations.AlterModelTable(
            name='modifiedrecordmodel',
            table='pdam_modifiedrecord',
        ),
        migrations.AlterModelTable(
            name='sensordatamodel',
            table='pdam_sensordata',
        ),
    ]
