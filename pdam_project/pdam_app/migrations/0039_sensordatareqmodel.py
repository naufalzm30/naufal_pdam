# Generated by Django 4.2.11 on 2024-07-23 08:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pdam_app', '0038_alter_checkerdatamodel_unique_together'),
    ]

    operations = [
        migrations.CreateModel(
            name='SensorDataReqModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('time', models.DateTimeField()),
                ('data', models.FloatField()),
                ('iteration', models.IntegerField()),
                ('channel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pdam_app.channelmodel')),
                ('sensor_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pdam_app.sensortypemodel')),
                ('station', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pdam_app.stationmodel')),
            ],
            options={
                'db_table': 'pdam_app_sensor_data_req',
            },
        ),
    ]
