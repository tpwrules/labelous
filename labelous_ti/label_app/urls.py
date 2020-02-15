from django.urls import path

from . import views
from . import tool_static_views

urlpatterns = [

    # the labeler needs a crapton of static files. we are allegedly clubbing
    # baby seals by serving them with django, but it works for now.
    path('', tool_static_views.tool),
    path('annotationTools/css/<file>', tool_static_views.lm_static,
        {"dir": "annotationTools/css"}),
    path('annotationTools/js/<file>', tool_static_views.lm_static,
        {"dir": "annotationTools/js"}),
    path('Icons/<file>', tool_static_views.lm_static,
        {"dir": "Icons"}),
    path('Images/f/<file>', tool_static_views.lm_static,
        {"dir": "Images/f"}),
    path('Annotations/f/<file>', tool_static_views.lm_static,
        {"dir": "Annotations/f"}),
]
