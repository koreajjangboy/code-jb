from django.test import TestCase
from django.urls import reverse

from .models import Project


class PageViewTests(TestCase):
    def test_pages_render_with_expected_template(self):
        pages = [
            ("home", "/", "pages/home.html"),
            ("about", "/about/", "pages/about.html"),
            ("projects", "/projects/", "pages/projects.html"),
        ]
        for name, path, template in pages:
            with self.subTest(name=name):
                self.assertEqual(reverse(name), path)
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)
                self.assertTemplateUsed(response, "base.html")

    def test_projects_page_content(self):
        response = self.client.get(reverse("projects"))
        self.assertContains(response, "<h1 class=\"text-metric mb-4\">Projects</h1>", html=True)
        self.assertContains(response, "code-jb.dev")
        self.assertContains(response, 'href="https://github.com/koreajjangboy/code-jb"')
        self.assertContains(response, 'rel="noopener noreferrer"')

    def test_navbar_marks_only_current_page_active(self):
        for current in ["home", "about", "projects"]:
            with self.subTest(current=current):
                response = self.client.get(reverse(current))
                for name in ["home", "about", "projects"]:
                    link = f'href="{reverse(name)}"'
                    active_link = f'class="nav-link active" {link} aria-current="page"'
                    if name == current:
                        self.assertContains(response, active_link, count=1)
                    else:
                        self.assertNotContains(response, active_link)
                self.assertContains(response, 'aria-current="page"', count=1)


class ProjectModelTests(TestCase):
    def test_seed_projects_exist(self):
        self.assertEqual(
            list(Project.objects.values(
                "name",
                "description",
                "technologies",
                "project_url",
                "github_url",
                "display_order",
                "is_published",
            )),
            [
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
            ],
        )

    def test_technology_list(self):
        project = Project(technologies="Python, Django, Bootstrap")
        self.assertEqual(project.technology_list, ["Python", "Django", "Bootstrap"])

    def test_technology_list_ignores_blank_entries(self):
        self.assertEqual(Project(technologies="").technology_list, [])
        self.assertEqual(Project(technologies=" Python , ,Django, ").technology_list, ["Python", "Django"])


class ProjectsPageTests(TestCase):
    def get_projects_page(self):
        response = self.client.get(reverse("projects"))
        self.assertEqual(response.status_code, 200)
        return response

    def test_published_projects_are_rendered(self):
        response = self.get_projects_page()
        self.assertContains(response, '<article class="col-12 col-md-6">', count=2)
        self.assertContains(
            response,
            "SNS-Assistant generates SNS posts and hashtags from images and keywords using the Gemini API.",
        )
        self.assertContains(response, "Python · Django · Bootstrap")
        self.assertContains(response, "Python · Streamlit · Gemini API · Pillow")

    def test_projects_are_rendered_in_display_order(self):
        content = self.get_projects_page().content.decode()
        self.assertLess(content.index(">code-jb.dev</a>"), content.index(">SNS-Assistant</a>"))

    def test_display_order_controls_rendering_order(self):
        Project.objects.filter(name="code-jb.dev").update(display_order=3)
        content = self.get_projects_page().content.decode()
        self.assertLess(content.index(">SNS-Assistant</a>"), content.index(">code-jb.dev</a>"))

    def test_unpublished_project_is_hidden(self):
        Project.objects.create(
            name="Hidden Project",
            description="This project is not published.",
            project_url="https://hidden.example.com",
            is_published=False,
        )
        response = self.get_projects_page()
        self.assertNotContains(response, "Hidden Project")
        self.assertNotContains(response, "https://hidden.example.com")
        self.assertContains(response, '<article class="col-12 col-md-6">', count=2)

    def test_project_and_github_urls_are_rendered(self):
        response = self.get_projects_page()
        links = [
            ("https://www.code-jb.dev", "code-jb.dev"),
            ("https://github.com/koreajjangboy/code-jb", "View on GitHub"),
            ("https://sns.code-jb.dev", "SNS-Assistant"),
            ("https://github.com/koreajjangboy/SNS-Assistant", "View on GitHub"),
        ]
        for url, text in links:
            with self.subTest(url=url):
                self.assertContains(
                    response,
                    f'<a href="{url}" target="_blank" rel="noopener noreferrer">{text}',
                    count=1,
                )

    def test_optional_urls_are_not_rendered_when_blank(self):
        Project.objects.create(
            name="Plain Project",
            description="A project without links.",
            display_order=3,
        )
        response = self.get_projects_page()
        self.assertContains(
            response,
            '<h2 class="card-title text-title">Plain Project</h2>',
            html=True,
        )
        self.assertContains(response, "View on GitHub", count=2)
        self.assertContains(response, 'target="_blank"', count=4)
