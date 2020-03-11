from django.shortcuts import render
from django.http import HttpResponse, Http404

import label_app.models

# show all the annotations the user has
def annotation_list(request):
    annotations = label_app.models.Annotation.objects.order_by('pk').filter(
        annotator=request.user, deleted=False)

    return render(request, "browser/labeling_imagelist.html", 
        {"annotations": annotations})

def credits_page(request):
    return render(request, "browser/credits.html")
