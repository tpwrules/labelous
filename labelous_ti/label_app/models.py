from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError

from image_mgr.models import Image

# an annotation: one set of polygons for a specific image by a specific person
class Annotation(models.Model):
    # who made this annotation
    annotator = models.ForeignKey(User, on_delete=models.CASCADE,
        related_name="annotations")
    # what image this annotation is for
    image = models.ForeignKey(Image, on_delete=models.CASCADE,
        related_name="annotations")
    # locked: if true, the annotator cannot touch it anymore
    locked = models.BooleanField(default=False)
    # finished: if true, the annotator considers it complete and wishes to
    # have it reviewed.
    finished = models.BooleanField(default=False)
    # deleted: if true, annotation can't be seen anymore
    deleted = models.BooleanField(default=False)
    # when this annotation was created
    creation_time = models.DateTimeField(auto_now_add=True)
    # when this annotation, or any of its polygons, was last changed.
    last_edit_time = models.DateTimeField()

def validate_is_points(value):
    if len(value) % 2 != 0:
        raise ValidationError("points must be x,y pairs. can't be odd length!")

# one polygon on an annotation
class Polygon(models.Model):
    # the annotation this polygon belongs to
    annotation = models.ForeignKey(Annotation,
        on_delete=models.CASCADE, related_name="polygons")
    # when this polygon was created
    creation_time = models.DateTimeField(auto_now_add=True)
    # when this polygon was last edited
    last_edit_time = models.DateTimeField()
    # this polygon's label. for now a string, but will be changed later
    label_as_str = models.CharField(max_length=255)
    # any notes the user attached to this polygon
    notes = models.TextField(blank=True)
    # the points in this polygon as consecutive x, y entries. we could use a
    # nested array, but it's hard to deal with in the admin interface. so
    # instead we just enforce that this field's length is a multiple of 2.
    points = ArrayField(models.FloatField(), validators=[validate_is_points])
    # occluded: if the polygon is considered occluded by another object.
    # the annotator has a checkbox to set it.
    occluded = models.BooleanField(default=False)
    # locked: if true, the annotator cannot touch it anymore
    locked = models.BooleanField(default=False)
    # deleted: if true, polygon can't be seen anymore
    deleted = models.BooleanField(default=False)
