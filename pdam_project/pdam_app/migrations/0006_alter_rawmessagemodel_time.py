# Generated by Django 4.2.11 on 2024-07-14 07:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pdam_app', '0005_rawmessagemodel_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rawmessagemodel',
            name='time',
            field=models.DateTimeField(unique=True),
        ),
    ]
