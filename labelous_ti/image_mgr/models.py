from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.urls import reverse

from label_app.filename_smuggler import encode_filename

# hold data about a particular image in the system
class Image(models.Model):
    # where the image is on the filesystem, relative to the image storage dir
    file_path = models.CharField(max_length=255)
    # available: true if image is available for annotation. if false, users can
    # see the image, and their own annotations (if any), but can't start
    # annotating this image.
    available = models.BooleanField(default=False)
    # deleted: if the image still exists. if it's deleted, users can't see it
    # even if they have annotations for it.
    deleted = models.BooleanField(default=False)
    # uploaded: if the image upload completed successfully. if this isn't true,
    # then the image was rejected for some reason, and it may not even be on
    # disk.
    uploaded = models.BooleanField(default=False)
    # original_hash: SHA-256 hash of the original file data. this lets us reject
    # duplicate images. additionally, if the original image's uploaded is False,
    # we can reject it early and avoid reprocessing bogus images.
    original_hash = models.BinaryField(max_length=32, unique=True)
    # dimensions of the original image. this is necessary to accurately handle
    # the annotation SVGs.
    image_x = models.IntegerField()
    image_y = models.IntegerField()
    # uploader: user who uploaded this image
    uploader = models.ForeignKey(User, on_delete=models.CASCADE)
    # upload_time: time when this image was uploaded. automatically set when
    # this object is created.
    upload_time = models.DateTimeField(auto_now_add=True)
    # priority: some metric of how important this image is. not sure what
    # it will be used for yet, if at all.
    priority = models.FloatField(default=1)

    class Meta:
        # enforce that non-uploaded images are always deleted. the rest of the
        # code checks deleted only, so we need this to hide non-uploaded
        # images.
        constraints = [
            models.CheckConstraint(check=
                (Q(uploaded=True) | (Q(uploaded=False) & Q(deleted=True))),
                name='not_uploaded_must_delete')
        ]

    # return the url of this image
    @property
    def image_url(self):
        return reverse("label_app:label_image", current_app="label_app",
            args=(encode_filename(image_id=self.pk),))
