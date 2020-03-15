from django.urls import path

from . import views
import image_mgr.views
from django.contrib.auth.decorators import login_required

app_name = "label_app"
urlpatterns = [
    path('',
        login_required(views.tool), name="label_tool"),
    path('Images/f/<str:filename>.jpg',
        image_mgr.views.image_file, name="label_image"),
    path('Images/t/<str:filename>.jpg',
        image_mgr.views.image_thumb_file, name="label_image_thumb"),
    path('Annotations/f/<str:filename>.svg',
        login_required(views.get_annotation_svg), name="anno_svg"),
    path('Annotations/f/<str:filename>.xml',
        login_required(views.get_annotation_xml), name="anno_xml"),
    path('annotationTools/perl/submit.cgi',
        login_required(views.post_annotation_xml)),
    path('annotationTools/perl/fetch_image.cgi',
        login_required(views.next_annotation)),
    path('annotationTools/perl/fetch_prev_image.cgi',
        login_required(views.prev_annotation)),
]
