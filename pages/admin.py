from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "display_order", "is_published"]
    list_editable = ["display_order", "is_published"]
