from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.uploadhandler import (
    FileUploadHandler, StopUpload, StopFutureHandlers
)

import shutil
import io

from .models import Image
from label_app.filename_smuggler import *
from .process_image import (process_image, MAX_IMAGE_SIZE,
    ProcessingFailure, UnacceptableImage)

# this custom upload handler stores the upload to memory, and then stops
# processing it if it's too big. amazingly, it doesn't actually seem possible to
# stop the upload, but we can at least stop storing more data.
class RestrictedSizeUploadHandler(FileUploadHandler):
    def __init__(self, request, max_size):
        super().__init__(request)
        self.max_size = max_size

    def new_file(self, *args, **kwargs):
        super().new_file(*args, **kwargs)

        self.received_size = 0
        self.chunks = []

        raise StopFutureHandlers() # we're doing this by ourselves

    def receive_data_chunk(self, raw_data, start):
        # make sure we haven't gone over the size limit
        self.received_size += len(raw_data)
        if self.received_size > self.max_size:
            # connection_reset=True should stop the upload. but it doesn't. it
            # does at least stop processing, so that the server can prepare a
            # "too big" response and get on with other things while the client
            # wastes its time.
            self.chunks = None
            raise StopUpload(connection_reset=True)
        # save the chunk of data
        self.chunks.append(raw_data)

    def file_complete(self, file_size):
        # glue all the chunks together
        data = b"".join(self.chunks)
        mem_file = InMemoryUploadedFile(
            # so we can turn it into a file type thing
            file=io.BytesIO(data),
            field_name=self.field_name,
            name=self.file_name,
            content_type=self.content_type,
            size=file_size,
            charset=self.charset,
            content_type_extra=self.content_type_extra
        )
        # make sure we're not wasting memory on the chunk data
        self.chunks = None
        return mem_file


# we need to play a bit of games with CSRF so we can install the custom handler.
# it needs to be installed before the check runs, so this function is exempt...
@login_required
@csrf_exempt
def upload_image(request):
    request.upload_handlers.insert(0, 
        RestrictedSizeUploadHandler(request, MAX_IMAGE_SIZE))
    return upload_image_view(request)

# ...but the function that does the actual work is still fully protected
@csrf_protect
def upload_image_view(request):
    if request.method == "POST":
        upload_image_post(request)
        return redirect("upload_image")

    return render(request, "image_mgr/upload.html")

def upload_image_post(request):
    # first, check that the file is okay
    if "the_image" not in request.FILES:
        # if the file didn't get sent, it probably got rejected by the uploader
        # because it was too big
        messages.add_message(request, messages.ERROR,
            "The image file is too large. Please mind the upload guidelines.")
        return

    the_image = request.FILES["the_image"]
    assert(the_image.size <= MAX_IMAGE_SIZE)

    the_image_data = the_image.read()
    # make sure the file starts like a JPEG. we ignore the content_type since
    # who knows what it could be. it might be right but what if it's wrong?
    if len(the_image_data) < 2 or the_image_data[:2] != b"\xff\xd8":
        messages.add_message(request, messages.ERROR,
            "The image format is not JPEG. Please mind the upload guidelines.")
        return
    # it may still not be a jpeg even though the header claims so!

    # but we let the processor handle that possibility. it returns whether or
    # not the image was new, or raises an exception if something went wrong.
    try:
        was_new = process_image(uploader=request.user,
            name=the_image.name, orig_data=the_image_data)
    except ProcessingFailure as e:
        print(str(e))
        messages.add_message(request, messages.ERROR,
            "The image appears corrupt. Please try a different image.")
        return
    except UnacceptableImage as e:
        # we stopped liking it in the middle of processing
        messages.add_message(request, messages.ERROR,
            str(e)+" Please mind the upload guidelines.")
        return

    if was_new:
        messages.add_message(request, messages.SUCCESS,
            "Thank you for your submission. The image will be reviewed"
            " by a moderator before it is available for annotation.")
    else:
        messages.add_message(request, messages.SUCCESS,
            "Thank you for your submission. Unfortunately, this image has"
            " already been submitted. Please try a different image.")

    # now that the processing is complete, the view will redirect the user back
    # to the upload page. if we just send the upload page again, then a refresh
    # would re-POST the data.
