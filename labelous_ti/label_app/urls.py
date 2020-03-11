from django.urls import path, re_path

from . import views
import image_mgr.views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('', login_required(views.tool)),
    re_path(r'^Images/f/img(?P<image_id>[0-9]+).jpg$',
        image_mgr.views.image_file),
    re_path(r'^Images/f/img(?P<image_id>[0-9]+).svg$',
        login_required(views.get_annotation_svg)),
    re_path(r'^Annotations/f/img(?P<image_id>[0-9]+).xml$',
        login_required(views.get_annotation_xml)),
    path('annotationTools/perl/submit.cgi',
        login_required(views.post_annotation_xml)),
    path('annotationTools/perl/fetch_image.cgi',
        login_required(views.next_annotation)),
    path('annotationTools/perl/fetch_prev_image.cgi',
        login_required(views.prev_annotation)),
]
