from django.urls import path, re_path
from django.shortcuts import render

from . import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('', lambda request: render(request, "browser/home.html"), name="home"),
    path('credits', views.credits_page, name="credits_page"),
    path('browse/in_progress/', login_required(views.annotation_list),
        name="annos_in_progress"),
]
