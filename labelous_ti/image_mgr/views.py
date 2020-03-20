from django.shortcuts import render, redirect
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

    # redirect user to the image without any extra stuff so the image cache
    # doesn't depend on the non-image part of the filename. this only applies to
    # full images since they are fetched through the tool.
    canonical = encode_filename(image_id=nd.image_id)
    if canonical != filename:
        return redirect(image.image_url, permanent=True)

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
