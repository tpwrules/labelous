# Generated by Django 3.0.3 on 2020-03-19 15:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('browser', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'verbose_name': 'user', 'verbose_name_plural': 'users'},
        ),
        migrations.AlterModelTable(
            name='user',
            table=None,
        ),
    ]
