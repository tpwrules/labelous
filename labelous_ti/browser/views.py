from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.core.exceptions import SuspiciousOperation
from django.contrib import messages
from django.db.models import OuterRef, Exists
from django.db import transaction
from django.contrib.admin.views.decorators import staff_member_required

from datetime import datetime, timezone

from image_mgr.models import Image
from label_app.models import Annotation

def credits_page(request):
    return render(request, "browser/credits.html")

# show all the annotations the user has and let them annotate them
def browse_view(request):
    if request.method == "POST":
        return handle_browse_modify(request)

    view_mode = request.resolver_match.url_name
    if view_mode == "annos_in_progress":
        locked = False
        finished = False
    elif view_mode == "annos_pending_review":
        locked = True
        finished = False
    elif view_mode == "annos_finished":
        locked = True
        finished = True

    annotations = Annotation.objects.order_by('pk').filter(
        annotator=request.user, deleted=False, locked=locked, finished=finished)

    return render(request, "browser/browse.html", 
        {"annotations": annotations})

# thrown when something went wrong while modifying like the conditions weren't
# met or the object doesn't exist
class ModificationFailure(Exception):
    pass

# handle the user doing something in the browser. the stuff comes via a hidden
# form so we can confirm with the user in JS and then POST the action and be
# sure the user did it via the CSRF token.
def handle_browse_modify(request):
    try:
        action = request.POST["action"]
        anno_id = request.POST["anno_id"]
        if action not in ("new", "delete", "review", "unreview"):
            raise Exception("invalid action {}".format(action))
    except Exception as e:
        raise SuspiciousOperation("bad post") from e

    if action == "new":
        try:
            with transaction.atomic():
                # get all the annotations the user is already working on or has
                # completed
                existing_annos = Annotation.objects.filter(
                    annotator=request.user, deleted=False)
                # then look for an image where an annotation for it doesn't
                # exist. we select for update so that another process can't turn
                # the same image into another annotation, but we skip locked so
                # that process can choose another image.
                new_image = Image.objects.select_for_update(
                    skip_locked=True).filter(~Exists(existing_annos.filter(
                        image__pk=OuterRef("pk"))))[0:1].get()
                # now we can create an annotation for it
                new_anno = Annotation(
                    annotator=request.user, image=new_image,
                    edit_key=b"", last_edit_time=datetime.now(timezone.utc))
                new_anno.save()
        except Image.DoesNotExist:
            messages.add_message(request, messages.ERROR,
                "There are no more images to annotate. Good job!")
            return redirect("annos_in_progress")
        # if everything went okay above, we can send the user off to edit their
        # shiny new annotation
        return redirect(new_anno.edit_url)

    try:
        anno_id = int(anno_id)
    except Exception as e:
        raise SuspiciousOperation("bad anno id") from e

    destination = request.resolver_match.url_name
    try:
        with transaction.atomic():
            # select for update so another process doesn't change the annotation
            # while we're changing it and put us in a weird state
            annotation = Annotation.objects.select_for_update().get(pk=anno_id,
                annotator=request.user, deleted=False, finished=False)

            if action == "delete":
                annotation.deleted = True
                messages.add_message(request, messages.SUCCESS,
                    "Annotation deleted.")
            elif action == "review":
                if annotation.locked:
                    raise ModificationFailure("can't review anno under review")
                annotation.locked = True
                messages.add_message(request, messages.SUCCESS,
                    "Annotation submitted for review.")
                destination = "annos_pending_review"
            elif action == "unreview":
                if not annotation.locked:
                    raise ModificationFailure(
                        "can't unreview anno not under review")
                annotation.locked = False
                messages.add_message(request, messages.SUCCESS,
                    "Annotation review cancelled.")
                destination = "annos_in_progress"

            annotation.save()
    except (Annotation.DoesNotExist, ModificationFailure):
        # these might happen if the user changes something in one tab and then
        # tries to mess with it again in another. we don't need to rudely
        # respond with a 400, we just kindly ask the user to do it again now
        # that the page is fresh.
        messages.add_message(request, messages.ERROR,
            "An inconsistency was detected. Please retry the operation.")

    return redirect(destination)


# let reviewers review others' annotations
@staff_member_required
def review_annotations(request):
    if request.method == "POST":
        try:
            action = request.POST["action"]
            anno_id = int(request.POST["item_id"])
            if action not in ("accept_anno", "reject_anno"):
                raise Exception("invalid action {}".format(action))
        except Exception as e:
            raise SuspiciousOperation("bad post") from e

        try:
            with transaction.atomic():
                # select for update so another process doesn't change the
                # annotation while we're changing it and put us in a weird
                # state
                annotation = Annotation.objects.select_for_update().get(
                    pk=anno_id, deleted=False, finished=False)

                if action == "accept_anno":
                    if not annotation.locked:
                        raise ModificationFailure(
                            "can't accept anno not under review")
                    annotation.finished = True
                    messages.add_message(request, messages.SUCCESS,
                        "Annotation accepted as complete.")
                elif action == "reject_anno":
                    if not annotation.locked:
                        raise ModificationFailure(
                            "can't reject anno not under review")
                    annotation.locked = False
                    messages.add_message(request, messages.SUCCESS,
                        "Annotation rejected and sent back to user.")

                annotation.save()
        except (Annotation.DoesNotExist, ModificationFailure):
            # these might happen if the user tries to change something while the
            # administrator is reviewing it. we don't need to rudely respond
            # with a 400, we just kindly ask the administrator to try again now
            # that the page is fresh.
            messages.add_message(request, messages.ERROR,
                "An inconsistency was detected. Please retry the operation.")

        return redirect("anno_review")

    annotations = Annotation.objects.order_by('pk').filter(
        deleted=False, locked=True, finished=False)

    return render(request, "browser/review.html", 
        {"annotations": annotations})

# and newly uploaded images
@staff_member_required
def review_images(request):
    if request.method == "POST":
        try:
            action = request.POST["action"]
            image_id = int(request.POST["item_id"])
            if action not in ("accept_image", "delete_image"):
                raise Exception("invalid action {}".format(action))
        except Exception as e:
            raise SuspiciousOperation("bad post") from e

        try:
            with transaction.atomic():
                # select for update so another process doesn't change the image
                # while we're changing it and put us in a weird state
                image = Image.objects.select_for_update().get(
                    pk=image_id, available=False, deleted=False)

                if action == "accept_image":
                    image.available = True
                    messages.add_message(request, messages.SUCCESS,
                        "Image now available for users to annotate.")
                elif action == "delete_image":
                    image.deleted = True
                    messages.add_message(request, messages.SUCCESS,
                        "Image deleted.")

                image.save()
        except (Image.DoesNotExist, ModificationFailure):
            # these might happen if the user tries to change something while the
            # administrator is reviewing it. we don't need to rudely respond
            # with a 400, we just kindly ask the administrator to try again now
            # that the page is fresh.
            messages.add_message(request, messages.ERROR,
                "An inconsistency was detected. Please retry the operation.")

        return redirect("image_review")

    images = Image.objects.order_by('pk').filter(
        available=False, visible=True)

    return render(request, "browser/review.html", 
        {"images": images})
