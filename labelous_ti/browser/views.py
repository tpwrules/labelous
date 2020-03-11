from django.shortcuts import render
from django.http import HttpResponse, Http404

import label_app.models

# show all the annotations the user has
def annotation_list(request):
    # this should be done with the templating engine but we are cowboys rn
    out = ["<html><head><title>My Annotations</title></head><body>"
        "<h1>My Annotations</h1>"]

    the_annotations = label_app.models.Annotation.objects.order_by('pk').filter(
        annotator=request.user, deleted=False)

    for anno in the_annotations:
        link = ("label/#collection=LabelMe&mode=f&folder=f"
            "&image=img{}.jpg&username=hi&actions=a".format(anno.image.pk))
        out.append("<a href='{}'>"
            "<div style='display:inline-block; margin-top:10px; width:25%;'>"
            "<img src='label/Images/f/img{}.jpg' style='width:100%;'>"
            "</div></a><br>".format(link, anno.image.pk))
    out.append("</body></html>")

    return HttpResponse(out)

def test(request):
    return render(request, "browser/base_labeling.html")

def credits_page(request):
    return render(request, "browser/credits.html")
