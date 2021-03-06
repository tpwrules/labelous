# Generated by Django 3.0.3 on 2020-03-19 15:34

from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import label_app.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('image_mgr', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Annotation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('locked', models.BooleanField(default=False)),
                ('finished', models.BooleanField(default=False)),
                ('deleted', models.BooleanField(default=False)),
                ('creation_time', models.DateTimeField(auto_now_add=True)),
                ('edit_key', models.BinaryField(max_length=16)),
                ('edit_version', models.IntegerField(default=0)),
                ('last_edit_time', models.DateTimeField()),
                ('score', models.FloatField(default=0)),
                ('annotator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='annotations', to=settings.AUTH_USER_MODEL)),
                ('image', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='annotations', to='image_mgr.Image')),
            ],
        ),
        migrations.CreateModel(
            name='Polygon',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_time', models.DateTimeField(auto_now_add=True)),
                ('last_edit_time', models.DateTimeField()),
                ('label_as_str', models.CharField(max_length=255)),
                ('notes', models.TextField(blank=True)),
                ('points', django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), size=None, validators=[label_app.models.validate_is_points])),
                ('occluded', models.BooleanField(default=False)),
                ('anno_index', models.IntegerField(blank=True, default=None, null=True)),
                ('locked', models.BooleanField(default=False)),
                ('deleted', models.BooleanField(default=False)),
                ('annotation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='polygons', to='label_app.Annotation')),
            ],
        ),
    ]
