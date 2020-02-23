# Generated by Django 3.0.3 on 2020-02-16 03:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('label_app', '0006_auto_20200215_1949'),
    ]

    operations = [
        migrations.AddField(
            model_name='annotation',
            name='edit_key',
            field=models.BinaryField(default=b'x', max_length=16),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='polygon',
            name='anno_index',
            field=models.IntegerField(blank=True, default=None, null=True),
        ),
    ]