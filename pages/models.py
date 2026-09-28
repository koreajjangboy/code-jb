from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    technologies = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma-separated, e.g. Python, Django, Bootstrap",
    )
    project_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name

    @property
    def technology_list(self):
        return [name.strip() for name in self.technologies.split(",") if name.strip()]


class GuestbookEntry(models.Model):
    name = models.CharField(max_length=50)
    message = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    # NULL for a top-level entry; otherwise the entry (or reply) this is a reply to.
    # Deleting an entry also deletes the replies below it.
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name_plural = "guestbook entries"

    def __str__(self):
        return self.name
