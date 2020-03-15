from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.conf import settings
from django.contrib.auth.decorators import login_required

import shutil

from .models import Image
from label_app.filename_smuggler import *

# serve images to the labeler
@login_required
def image_file(request, filename):
    # load image while making sure that it hasn't been deleted
    try:
        nd = decode_filename(filename, image_id=True)
        image = Image.objects.get(pk=nd.image_id, deleted=False)
    except Exception as e:
        raise Http404("Image does not exist.") from e

    # still clubbing baby seals
    f = open(image.image_path, "rb")
    resp = HttpResponse(content_type="image/jpeg")
    shutil.copyfileobj(f, resp)
    f.close()
    return resp

# serve image thumbnails
@login_required
def image_thumb_file(request, filename):
    # load image while making sure that it hasn't been deleted
    try:
        nd = decode_filename(filename, image_id=True)
        image = Image.objects.get(pk=nd.image_id, deleted=False)
    except Exception as e:
        raise Http404("Image does not exist.") from e

    # still clubbing baby seals
    f = open(image.thumb_path, "rb")
    resp = HttpResponse(content_type="image/jpeg")
    shutil.copyfileobj(f, resp)
    f.close()
    return resp
