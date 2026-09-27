from django.db import migrations


PROJECTS = [
    {
        "name": "code-jb.dev",
        "description": (
            "code-jb.dev is my personal website, built with Django "
            "as a space for development, projects, and creative expression."
        ),
        "technologies": "Python, Django, Bootstrap",
        "project_url": "https://www.code-jb.dev",
        "github_url": "https://github.com/koreajjangboy/code-jb",
        "display_order": 1,
        "is_published": True,
    },
    {
        "name": "SNS-Assistant",
        "description": (
            "SNS-Assistant generates SNS posts and hashtags "
            "from images and keywords using the Gemini API."
        ),
        "technologies": "Python, Streamlit, Gemini API, Pillow",
        "project_url": "https://sns.code-jb.dev",
        "github_url": "https://github.com/koreajjangboy/SNS-Assistant",
        "display_order": 2,
        "is_published": True,
    },
]


def seed_projects(apps, schema_editor):
    Project = apps.get_model("pages", "Project")
    for data in PROJECTS:
        defaults = {key: value for key, value in data.items() if key != "name"}
        Project.objects.update_or_create(name=data["name"], defaults=defaults)


def unseed_projects(apps, schema_editor):
    Project = apps.get_model("pages", "Project")
    Project.objects.filter(name__in=[data["name"] for data in PROJECTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_projects, unseed_projects),
    ]
