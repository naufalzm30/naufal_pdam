# Generated by Django 4.2.11 on 2024-07-27 03:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pdam_app', '0047_rename_loggermodel_loggertypemodel'),
    ]

    operations = [
        migrations.AddField(
            model_name='stationmodel',
            name='logger_type',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='pdam_app.loggertypemodel'),
            preserve_default=False,
        ),
    ]