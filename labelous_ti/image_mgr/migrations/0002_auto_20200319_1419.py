# Generated by Django 3.0.3 on 2020-03-19 19:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('image_mgr', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='image',
            name='priority',
        ),
        migrations.AddField(
            model_name='image',
            name='num_images',
            field=models.IntegerField(default=0),
        ),
    ]
