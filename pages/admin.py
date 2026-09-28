from django.contrib import admin

from .models import GuestbookEntry, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "display_order", "is_published"]
    list_editable = ["display_order", "is_published"]


@admin.register(GuestbookEntry)
class GuestbookEntryAdmin(admin.ModelAdmin):
    list_display = ["name", "message", "parent", "created_at"]
    list_filter = [("parent", admin.EmptyFieldListFilter)]
    list_select_related = ["parent"]
    search_fields = ["name", "message", "parent__name"]
    raw_id_fields = ["parent"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at"]
