# Generated by Django 4.2.11 on 2024-09-07 02:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account_app', '0006_alter_user_email_alter_user_first_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='balai',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='account_app.balaimodel'),
        ),
    ]