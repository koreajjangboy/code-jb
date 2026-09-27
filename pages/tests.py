from django.test import TestCase
from django.urls import reverse


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
