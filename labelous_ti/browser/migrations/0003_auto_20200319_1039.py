# Generated by Django 3.0.3 on 2020-03-19 15:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('browser', '0002_auto_20200319_1036'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=254, unique=True),
        ),
    ]
