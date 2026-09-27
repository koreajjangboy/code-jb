from django.shortcuts import render


def home(request):
    return render(request, "pages/home.html")


def about(request):
    return render(request, "pages/about.html")


def projects(request):
    return render(request, "pages/projects.html")