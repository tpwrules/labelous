from django.urls import path, re_path

from . import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('', login_required(views.annotation_list)),
    path('credits', views.credits_page, name="credits_page"),
]
