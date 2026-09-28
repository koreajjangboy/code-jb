from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("projects/", views.projects, name="projects"),
    path("guestbook/", views.guestbook, name="guestbook"),
    path("guestbook/<int:entry_id>/reply/", views.guestbook_reply, name="guestbook_reply"),
]