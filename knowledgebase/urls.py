from django.urls import path
from . import views

urlpatterns = [
    path("", views.kb_list, name="kb_list"),
    path("create/", views.kb_create, name="kb_create"),
    path("<int:pk>/edit/", views.kb_edit, name="kb_edit"),
    path("<int:pk>/archive/", views.kb_archive, name="kb_archive"),
    path("<int:pk>/", views.kb_detail, name="kb_detail"),
]
