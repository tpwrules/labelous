from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.conf import settings

import shutil

from . import models
from .tool_static_views import lm_static

# serve images to the labeler
def image_file(request, image_id):
    # regex only allows numbers through
    image_id = int(image_id)

    try:
        image = models.Image.objects.get(pk=image_id)
        exists = True
    except models.Image.DoesNotExist:
        exists = False

    if not exists or not image.visible:
        raise Http404("Image does not exist.")

    # still clubbing baby seals
    f = open(settings.L_IMAGE_PATH/image.file_path, "rb")
    resp = HttpResponse(content_type="image/jpeg")
    shutil.copyfileobj(f, resp)
    f.close()
    return resp
