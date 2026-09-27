from django.shortcuts import render

from .models import Project


def home(request):
    return render(request, "pages/home.html")


def about(request):
    return render(request, "pages/about.html")


def projects(request):
    projects = Project.objects.filter(is_published=True)
    return render(
        request,
        "pages/projects.html",
        {"projects": projects},
    )