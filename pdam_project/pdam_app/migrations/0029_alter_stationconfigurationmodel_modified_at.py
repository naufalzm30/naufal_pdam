# Generated by Django 4.2.11 on 2024-07-19 06:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pdam_app', '0028_alter_stationconfigurationmodel_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stationconfigurationmodel',
            name='modified_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]