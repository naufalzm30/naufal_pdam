# Generated by Django 4.2.11 on 2024-08-26 05:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account_app', '0003_balaimodel_user_balai'),
        ('pdam_app', '0059_stationmodel_balai_alter_loggertypemodel_logger_ver_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stationmodel',
            name='balai',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='account_app.balaimodel'),
        ),
    ]