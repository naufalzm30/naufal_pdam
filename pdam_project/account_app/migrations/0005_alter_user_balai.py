# Generated by Django 4.2.11 on 2024-08-31 10:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account_app', '0004_alter_user_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='balai',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='account_app.balaimodel'),
        ),
    ]