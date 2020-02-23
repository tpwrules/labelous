from django.urls import path, re_path

from . import views
from . import tool_static_views
import image_mgr.views

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
    re_path(r'^Images/f/img(?P<image_id>[0-9]+).jpg$',
        image_mgr.views.image_file),
    re_path(r'^Annotations/f/img(?P<image_id>[0-9]+).xml$',
        views.get_annotation_xml),
    path('annotationTools/perl/submit.cgi', views.post_annotation_xml),
    path('annotationTools/perl/fetch_image.cgi', views.next_annotation),
    path('annotationTools/perl/fetch_prev_image.cgi', views.prev_annotation),
]
