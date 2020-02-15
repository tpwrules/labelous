from django.db import models
from django.contrib.auth.models import User

# hold data about a particular image in the system
class Image(models.Model):
    # where the image is on the filesystem, relative to the image storage dir
    file_path = models.CharField(max_length=255)
    # available: true if image is available for annotation. if false, users
    # can see their own annotations (if any) but can't start annotating this
    # image.
    available = models.BooleanField(default=False)
    # visible: true if the image can be seen by users. if false, users can't
    # see the image even if they have annotations for it.
    visible = models.BooleanField(default=False)
    # uploader: user who uploaded this image
    uploader = models.ForeignKey(User, on_delete=models.CASCADE)
    # upload_time: time when this image was uploaded. automatically set when
    # this object is created.
    upload_time = models.DateTimeField(auto_now_add=True)
    # priority: some metric of how important this image is. not sure what
    # it will be used for yet, if at all.
    priority = models.FloatField(default=1)
