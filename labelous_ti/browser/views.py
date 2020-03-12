from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404
from django.core.exceptions import SuspiciousOperation
from django.contrib import messages

import label_app.models

# show all the annotations the user has
def annotation_list(request):
    if request.method == "POST":
        return redirect(handle_modify(request))

    annotations = label_app.models.Annotation.objects.order_by('pk').filter(
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
        if action not in ("delete_anno",):
            raise Exception("invalid action {}".format(action))
    except Exception as e:
        raise SuspiciousOperation("bad post") from e

    if action != "annotate_new":
        try:
            anno_id = int(anno_id)
            annotation = label_app.models.Annotation.objects.get(pk=anno_id,
                annotator=request.user, deleted=False, finished=False)
        except Exception as e:
            raise SuspiciousOperation("bad annotation") from e

    if action == "delete_anno":
        annotation.deleted = True
        annotation.save()
        messages.add_message(request, messages.SUCCESS, "Annotation deleted.")

    return request.resolver_match.url_name
