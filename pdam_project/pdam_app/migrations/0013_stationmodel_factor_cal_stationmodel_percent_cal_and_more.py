# Generated by Django 4.2.11 on 2024-07-16 09:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pdam_app', '0012_rename_date_time_checkerdatamodel_time_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='stationmodel',
            name='factor_cal',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='stationmodel',
            name='percent_cal',
            field=models.FloatField(default=0),
        ),
        migrations.CreateModel(
            name='ModifiedRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('percent_cal', models.FloatField()),
                ('factor_cal', models.BooleanField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expired_at', models.DateTimeField(blank=True, null=True)),
                ('station', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pdam_app.stationmodel')),
            ],
        ),
    ]
