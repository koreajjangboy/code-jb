from django.db import migrations


PROJECT = {
    "name": "Advertisement-Video-Generator",
    "description": (
        "Advertisement-Video-Generator automatically creates 9:16 short-form ad videos, "
        "from Gemini-written scripts and TTS narration to Luma scene clips and FFmpeg rendering."
    ),
    "technologies": "Python, FastAPI, PostgreSQL, Gemini API, Luma API, FFmpeg",
    "project_url": "",
    "github_url": "https://github.com/koreajjangboy/Advertisement-Video-Generator",
    "display_order": 3,
    "is_published": True,
}


def seed_project(apps, schema_editor):
    Project = apps.get_model("pages", "Project")
    defaults = {key: value for key, value in PROJECT.items() if key != "name"}
    Project.objects.update_or_create(name=PROJECT["name"], defaults=defaults)


def unseed_project(apps, schema_editor):
    Project = apps.get_model("pages", "Project")
    Project.objects.filter(name=PROJECT["name"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0004_guestbookentry_parent"),
    ]

    operations = [
        migrations.RunPython(seed_project, unseed_project),
    ]
