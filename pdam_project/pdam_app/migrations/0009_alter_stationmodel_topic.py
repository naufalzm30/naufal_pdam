# Generated by Django 4.2.11 on 2024-07-14 07:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pdam_app', '0008_alter_rawmessagemodel_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stationmodel',
            name='topic',
            field=models.CharField(max_length=100, unique=True),
        ),
    ]