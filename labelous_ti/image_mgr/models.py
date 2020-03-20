from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.conf import settings

import math

from browser.models import User
from label_app.filename_smuggler import encode_filename

# maximum size of thumbnail in each dimension. we want thumbnails to all be the
# same height, so we allow a 3:1 aspect ratio. images that wide probably won't
# ever be uploaded (but it's okay if they are, we will pad the box)
THUMBNAIL_SIZE = (576, 192)

# hold data about a particular image in the system
class Image(models.Model):
    # where the image is on the filesystem, relative to the image storage dir
    file_path = models.CharField(max_length=255)
    # available: true if image is available for annotation. if false, users can
    # see the image and their own annotations (if any), but can't start
    # annotating this image.
    available = models.BooleanField(default=False)
    # deleted: if the image still exists. if it's deleted, users can't see it
    # or any annotations they have for it.
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
    # num_annotations: how many annotations there are for this image. not
    # necessarily 100% accurate. used to give users the image with the least
    # annotations.
    num_annotations = models.IntegerField(default=0)

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

    # return the url of this image's thumbnail
    @property
    def image_thumb_url(self):
        return reverse("label_app:label_image_thumb", current_app="label_app",
            args=(encode_filename(image_id=self.pk),))

    # path to the image file on disk
    @property
    def image_path(self):
        return settings.L_IMAGE_PATH/(self.file_path+".jpg")

    # path to the image thumbnail file on disk
    @property
    def thumb_path(self):
        return settings.L_IMAGE_PATH/(self.file_path+"_thumb.jpg")

    # path to x-accel-redirect version of image
    @property
    def image_redir_path(self):
        return "/image_real/{}.jpg".format(self.file_path)

    # path to x-accel-redirect version of thumbnail
    @property
    def thumb_redir_path(self):
        return "/image_real/{}_thumb.jpg".format(self.file_path)

    # tuple of image (width, height)
    @property
    def image_size(self):
        return (self.image_x, self.image_y)

    # tuple of thumbnail (width, height)
    # since we use PIL to generate the thumbnails, we borrow PIL's math
    @property
    def thumb_size(self):
        x, y = THUMBNAIL_SIZE

        def round_aspect(number, key):
            return max(min(math.floor(number), math.ceil(number), key=key), 1)

        # preserve aspect ratio
        aspect = self.image_x / self.image_y
        if x / y >= aspect:
            x = round_aspect(y * aspect, key=lambda n: abs(aspect - n / y))
        else:
            y = round_aspect(x / aspect, key=lambda n: abs(aspect - x / n))

        return (x, y)
