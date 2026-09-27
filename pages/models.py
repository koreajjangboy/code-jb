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
