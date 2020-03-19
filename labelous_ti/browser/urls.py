from django.urls import path, re_path
from django.shortcuts import render

from . import views
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('credits', views.credits_page, name="credits_page"),

    path('browse/in_progress/', login_required(views.browse_view),
        name="annos_in_progress"),
    path('browse/pending_review/', login_required(views.browse_view),
        name="annos_pending_review"),
    path('browse/finished/', login_required(views.browse_view),
        name="annos_finished"),

    path('review/annotations/', login_required(views.review_annotations),
        name="anno_review"),
    path('review/images/', login_required(views.review_images),
        name="image_review"),

    path('', auth_views.LoginView.as_view(
        redirect_authenticated_user=True), name="login"),
    path('account/logout/', auth_views.LogoutView.as_view(), name="logout"),
]
