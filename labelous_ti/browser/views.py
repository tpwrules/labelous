from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.core.exceptions import SuspiciousOperation
from django.contrib import messages
from django.db.models import OuterRef, Exists

from datetime import datetime, timezone

from image_mgr.models import Image
from label_app.models import Annotation

# show all the annotations the user has
def annotation_list(request):
    if request.method == "POST":
        return handle_modify(request)

    annotations = Annotation.objects.order_by('pk').filter(
        annotator=request.user, deleted=False)

    return render(request, "browser/browse.html", 
        {"annotations": annotations})

def credits_page(request):
    return render(request, "browser/credits.html")

# handle the user doing something in the browser. the stuff comes via a hidden
# form so we can confirm with the user in JS and then POST the action and be
# sure the user did it via the CSRF token.
def handle_modify(request):
    try:
        action = request.POST["action"]
        anno_id = request.POST["anno_id"]
        if action not in ("delete_anno", "new_anno",):
            raise Exception("invalid action {}".format(action))
    except Exception as e:
        raise SuspiciousOperation("bad post") from e

    if action != "new_anno":
        try:
            anno_id = int(anno_id)
            annotation = Annotation.objects.get(pk=anno_id,
                annotator=request.user, deleted=False, finished=False)
        except Exception as e:
            raise SuspiciousOperation("bad annotation") from e
    else:
        anno_id = None

    if action == "delete_anno":
        annotation.deleted = True
        annotation.save()
        messages.add_message(request, messages.SUCCESS, "Annotation deleted.")
    elif action == "new_anno":
        # get all the annotations the user is already working or has completed
        existing_annos = Annotation.objects.filter(
            annotator=request.user, deleted=False)
        # then look for an image where an annotation for it doesn't exist
        new_image = Image.objects.filter(
            ~Exists(existing_annos.filter(image__pk=OuterRef("pk"))))[0:1]
        try:
            new_image = new_image.get()
        except Image.DoesNotExist:
            messages.add_message(request, messages.ERROR,
                "There are no more images to annotate. Good job!")
            return redirect("annos_in_progress")
        
        # if one exists, create an annotation for it
        new_anno = Annotation(
            annotator=request.user, image=new_image,
            edit_key=b"", last_edit_time=datetime.now(timezone.utc))
        new_anno.save()

        # then send the user off to edit it
        return redirect(new_anno.edit_url)

    return redirect(request.resolver_match.url_name)
