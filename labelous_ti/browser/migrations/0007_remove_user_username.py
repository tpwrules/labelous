# Generated by Django 3.0.3 on 2020-03-19 20:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('browser', '0006_auto_20200319_1503'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='username',
        ),
    ]
