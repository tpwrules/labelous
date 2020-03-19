from django.shortcuts import render, redirect, reverse
from django.http import HttpResponse, Http404
from django.core.exceptions import SuspiciousOperation, ValidationError
from django.contrib import messages
from django.db.models import OuterRef, Exists
from django.db import IntegrityError, transaction
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.password_validation import (
    validate_password, password_validators_help_texts)
from django.contrib.auth import authenticate

from datetime import datetime, timezone
import secrets

from .models import User
from image_mgr.models import Image
from label_app.models import Annotation

def credits_page(request):
    return render(request, "browser/credits.html")

# show all the annotations the user has and give them options to edit the
# annotation or otherwise modify them
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
        annotator=request.user, deleted=False, locked=locked, finished=finished,
        image__deleted=False)

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
                # then look for an image that the user doesn't already have an
                # annotation for. we select for update so that another process
                # can't turn the same image into another annotation, but we skip
                # locked so that that process can choose another image.
                not_on_existing_anno = ~Exists(existing_annos.filter(
                    image__pk=OuterRef("pk")))
                # we pick the image with the least number of existing
                # annotations so that no image gets left behind
                new_image = Image.objects.select_for_update(
                    skip_locked=True).filter(not_on_existing_anno).filter(
                        available=True, deleted=False).order_by(
                            "num_annotations")[0:1].get()
                # now we can create an annotation for that image
                new_anno = Annotation(
                    annotator=request.user, image=new_image,
                    edit_key=b"", last_edit_time=datetime.now(timezone.utc))
                new_anno.save()
                # mark that the image has another annotation attached
                new_image.num_annotations += 1
                new_image.save()
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
                # subtract 1 from the associated image's annotation count
                # because one less annotation exists
                image = Image.objects.select_for_update().get(
                    pk=annotation.image.pk)
                image.num_annotations -= 1
                image.save()
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
                "An inconsistency has been detected. This may occur if "
                "operations on the same annotation are attempted in multiple "
                "tabs. Please retry the operation.")

    return redirect(destination)


# let reviewers review others' annotations
@permission_required("browser.reviewer", raise_exception=True)
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
                "An inconsistency has been detected. This may occur if "
                "operations on the same annotation are attempted in multiple "
                "tabs. Please retry the operation.")

        return redirect("anno_review")

    annotations = Annotation.objects.order_by('pk').filter(
        deleted=False, locked=True, finished=False, image__deleted=False)

    return render(request, "browser/review.html", 
        {"annotations": annotations})

# and newly uploaded images
@permission_required("browser.reviewer", raise_exception=True)
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
                "An inconsistency has been detected. This may occur if "
                "operations on the same annotation are attempted in multiple "
                "tabs. Please retry the operation.")

        return redirect("image_review")

    images = Image.objects.order_by('pk').filter(
        available=False, deleted=False)

    return render(request, "browser/review.html", 
        {"images": images})


def account_info(request):
    user = request.user
    if "user" in request.GET and request.GET["user"] != "":
        if request.user.has_perm("browser.account_manager"):
            try:
                user = User.objects.get(email=request.GET["user"])
            except User.DoesNotExist:
                messages.add_message(request, messages.ERROR,
                    "User doesn't exist.")
        else:
            # user isn't authorized to look up other users. normally the user
            # wouldn't see the form, so we can be a little snarky at users who
            # tried to poke at things
            messages.add_message(request, messages.ERROR,
                "Mind your own business.")

    return render(request, "browser/account.html",
        {"info_email": user.email})

def do_changepw(request):
    if request.user.is_authenticated:
        try:
            old_pw = request.POST["old_pw"]
            new_pw1 = request.POST["new_pw1"]
            new_pw2 = request.POST["new_pw2"]
        except KeyError:
            messages.add_message(request, messages.ERROR,
                "Something went wrong. Please try again.")
            return
        if authenticate(email=request.user.email, password=old_pw) is None:
            messages.add_message(request, messages.ERROR,
                "Password is incorrect.")
            return
        user = request.user
    else:
        try:
            token = request.POST["token"]
            new_pw1 = request.POST["new_pw1"]
            new_pw2 = request.POST["new_pw2"]
        except KeyError:
            messages.add_message(request, messages.ERROR,
                "Something went wrong. Please try again.")
            return
        try:
            user = User.objects.get(password_reset_token=bytes.fromhex(token))
        except (User.DoesNotExist, ValueError):
            messages.add_message(request, messages.ERROR,
                "Password reset token is incorrect.")
            return

    if new_pw1 != new_pw2:
        messages.add_message(request, messages.ERROR,
            "Passwords do not match.")
        return
    try:
        validate_password(new_pw1, user=user)
    except ValidationError as e:
        messages.add_message(request, messages.ERROR,
            "Password not changed: "+",".join(e))
        return

    user.set_password(new_pw1)
    user.password_reset_token = None
    user.save()
    messages.add_message(request, messages.SUCCESS,
        "Password changed successfully.") 


def account_changepw(request):
    try:
        password_reset_token = request.GET["token"]
    except KeyError:
        password_reset_token = ""

    if request.method == "POST":
        do_changepw(request)

    return render(request, "browser/account.html",
        {"password_helps": password_validators_help_texts(),
         "password_reset_token": password_reset_token})

# make a reset token, set it on the user, then return the display version
def set_reset_token(user):
    token = secrets.token_bytes(16)
    user.password_reset_token = token
    return token.hex()

def do_create_account(request):
    new_email = request.POST["create_email"]
    new_user = User.objects.create_user(new_email)
    # create reset token so user can change their password
    reset_token = set_reset_token(new_user)
    new_user.save()
    return reset_token

@permission_required("browser.account_manager", raise_exception=True)
def account_create(request):
    token_url = None
    if request.method == "POST":
        try:
            reset_token = do_create_account(request)
            token_url = request.build_absolute_uri(
                reverse("account_changepw")+"?token="+reset_token)
        except IntegrityError:
            messages.add_message(request, messages.ERROR,
                "User with that e-mail already exists.")
        else:
            messages.add_message(request, messages.SUCCESS,
                "User created successfully.")

    return render(request, "browser/account.html",
        {"token_url": token_url})

@permission_required("browser.account_manager", raise_exception=True)
def account_maketoken(request):
    token_url = None
    if request.method == "POST":
        try:
            user = User.objects.get(email=request.POST["reset_email"])
        except User.DoesNotExist:
            messages.add_message(request, messages.ERROR,
                "User doesn't exist.")
        else:
            reset_token = set_reset_token(user)
            user.save()
            token_url = request.build_absolute_uri(
                reverse("account_changepw")+"?token="+reset_token)

    return render(request, "browser/account.html",
        {"token_url": token_url})
