# Generated by Django 4.2.11 on 2024-08-29 04:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pdam_app', '0060_alter_stationmodel_balai'),
    ]

    operations = [
        migrations.AlterField(
            model_name='thresholdsensormodel',
            name='day',
            field=models.PositiveIntegerField(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')]),
        ),
        migrations.AlterField(
            model_name='thresholdsensormodel',
            name='hour',
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name='thresholdsensormodel',
            name='minute',
            field=models.PositiveIntegerField(),
        ),
        migrations.CreateModel(
            name='PublishThresholdModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.PositiveIntegerField(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')])),
                ('hour', models.PositiveIntegerField()),
                ('message', models.CharField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_sent', models.BooleanField(default=False)),
                ('receive_time', models.DateTimeField()),
                ('station', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pdam_app.stationmodel')),
            ],
            options={
                'db_table': 'pdam_publish_threshold',
            },
        ),
    ]
