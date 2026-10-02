import urllib.parse
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from . import creative_works
from .models import GuestbookEntry, Project


class PageViewTests(TestCase):
    def test_pages_render_with_expected_template(self):
        pages = [
            ("home", "/", "pages/home.html"),
            ("projects", "/projects/", "pages/projects.html"),
            ("guestbook", "/guestbook/", "pages/guestbook.html"),
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
        for current in ["projects", "guestbook"]:
            with self.subTest(current=current):
                response = self.client.get(reverse(current))
                for name in ["projects", "guestbook"]:
                    link = f'href="{reverse(name)}"'
                    active_link = f'class="nav-link active" {link} aria-current="page"'
                    if name == current:
                        self.assertContains(response, active_link, count=1)
                    else:
                        self.assertNotContains(response, active_link)
                self.assertContains(response, 'aria-current="page"', count=1)

    def test_navbar_has_brand_and_no_home_or_about_links(self):
        for path in ["/", "/projects/", "/guestbook/"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertContains(response, '<a class="navbar-brand" href="/"', count=1)
                self.assertContains(response, ">code-jb.dev</a>")
                self.assertNotContains(response, ">JB Kim</a>")
                self.assertEqual(
                    [link.split(">")[-1] for link in response.content.decode().split("</a>") if 'class="nav-link' in link],
                    ["Projects", "Guestbook"],
                )
                self.assertNotContains(response, 'href="/about/"')

    def test_brand_is_current_page_on_home(self):
        response = self.client.get("/")
        self.assertContains(response, '<a class="navbar-brand" href="/" aria-current="page">code-jb.dev</a>', count=1)
        self.assertContains(response, 'aria-current="page"', count=1)

    def test_home_includes_about_section(self):
        response = self.client.get("/")
        self.assertContains(response, '<h1 class="text-metric mb-3">Code is how I build. Art is how I express.</h1>', html=True)
        self.assertContains(response, 'id="about"')
        self.assertContains(response, '<h2 id="about-heading" class="text-title mb-3">About Me</h2>', html=True)
        for text in ["I am JB Kim, a developer and artist.", "Skills", "Current Focus", "<li>PostgreSQL</li>",
                     "I want to think in my own words"]:
            with self.subTest(text=text):
                self.assertContains(response, text)
        self.assertContains(response, "Code is how I build. Art is how I express.", count=1)

    def test_home_intro_and_current_focus_copy(self):
        content = self.client.get("/").content.decode()
        intro = content[content.index("</h1>"):content.index('id="about"')]
        self.assertIn("Where technology meets art, I build practical projects that give ideas a real shape.", intro)
        self.assertNotIn("Step by step", intro)
        focus = content[content.index(">Current Focus</h3>"):content.index('id="creative-works-heading"')]
        for text in [
            '<p class="focus-title">Education for the AI Generation</p>',
            '<p class="focus-text">Helping the next generation grow with confidence in the age of AI.</p>',
            '<p class="focus-title">Emotional Steadiness</p>',
            '<p class="focus-text">Balancing everyday life and creative work to stay immersed for the long run.</p>',
        ]:
            with self.subTest(text=text):
                self.assertIn(text, focus)
        self.assertNotIn("focus-caption", focus)

    def test_tech_keywords_only_remain_in_skills(self):
        content = self.client.get("/").content.decode()
        jb_card = content[content.index(">JB Kim</h3>"):content.index(">Skills</h3>")]
        skills = content[content.index(">Skills</h3>"):content.index(">Current Focus</h3>")]
        intro = content[content.index("</h1>"):content.index('id="about"')]
        focus = content[content.index(">Current Focus</h3>"):content.index('id="creative-works-heading"')]
        for name, section in [("intro", intro), ("JB Kim card", jb_card), ("Current Focus", focus)]:
            for keyword in ["Python", "Django", "PostgreSQL", "data analysis", "AI"]:
                # "AI" is part of the approved Current Focus topic (Education for the AI Generation).
                if name == "Current Focus" and keyword == "AI":
                    continue
                with self.subTest(section=name, keyword=keyword):
                    self.assertNotIn(keyword, section)
        for item in ["Python", "Django", "PostgreSQL", "Git / GitHub", "Docker", "Data Analysis", "AI / Automation"]:
            with self.subTest(skill=item):
                self.assertIn(f"<li>{item}</li>", skills)
        self.assertIn("I turn ideas into projects.", jb_card)
        self.assertNotIn("I connect technology and creativity through practical projects.", jb_card)

    def test_about_url_redirects_to_home_section(self):
        self.assertEqual(reverse("about"), "/about/")
        response = self.client.get("/about/")
        self.assertRedirects(response, "/#about", status_code=301)


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
        self.assertLess(content.index(">code-jb.dev</h2>"), content.index(">SNS-Assistant</h2>"))

    def test_display_order_controls_rendering_order(self):
        Project.objects.filter(name="code-jb.dev").update(display_order=3)
        content = self.get_projects_page().content.decode()
        self.assertLess(content.index(">SNS-Assistant</h2>"), content.index(">code-jb.dev</h2>"))

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

    def test_project_titles_are_not_links(self):
        response = self.get_projects_page()
        for name in ["code-jb.dev", "SNS-Assistant"]:
            with self.subTest(name=name):
                self.assertContains(
                    response,
                    f'<h2 class="card-title text-title">{name}</h2>',
                    html=True,
                )
        self.assertNotContains(response, 'href="https://www.code-jb.dev"')
        self.assertNotContains(response, 'href="https://sns.code-jb.dev"')

    def test_github_urls_are_rendered(self):
        response = self.get_projects_page()
        for url in [
            "https://github.com/koreajjangboy/code-jb",
            "https://github.com/koreajjangboy/SNS-Assistant",
        ]:
            with self.subTest(url=url):
                self.assertContains(
                    response,
                    f'<a href="{url}" target="_blank" rel="noopener noreferrer">View on GitHub',
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
        self.assertContains(response, 'target="_blank"', count=2)


class GuestbookTests(TestCase):
    url = "/guestbook/"

    def post(self, name="JB", message="Hello"):
        return self.client.post(self.url, {"name": name, "message": message})

    def assertRejected(self, response, field):
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/guestbook.html")
        self.assertIn(field, response.context["form"].errors)
        self.assertContains(response, 'class="form-field form-field-invalid"')
        self.assertContains(response, f'id="id_{field}_error"')
        self.assertEqual(GuestbookEntry.objects.count(), 0)

    def test_get_shows_form_and_empty_state(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h1 class="text-metric guestbook-title">Guestbook</h1>', html=True)
        self.assertContains(response, 'method="post"')
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, 'maxlength="50"')
        self.assertContains(response, 'maxlength="1000"')
        self.assertContains(response, "No messages yet.")

    def test_valid_post_saves_and_redirects(self):
        response = self.post(name="Hong Gildong", message="Nice site!")
        self.assertRedirects(response, self.url)
        entry = GuestbookEntry.objects.get()
        self.assertEqual((entry.name, entry.message), ("Hong Gildong", "Nice site!"))
        self.assertIsNotNone(entry.created_at)

        page = self.client.get(self.url)
        self.assertContains(page, "Hong Gildong")
        self.assertContains(page, "Nice site!")
        self.assertContains(page, f'datetime="{entry.created_at.isoformat()}"')
        self.assertNotContains(page, "No messages yet.")

    def test_empty_name_is_rejected(self):
        self.assertRejected(self.post(name=""), "name")

    def test_whitespace_only_name_is_rejected(self):
        self.assertRejected(self.post(name="   "), "name")

    def test_empty_message_is_rejected(self):
        self.assertRejected(self.post(message=""), "message")

    def test_name_longer_than_50_is_rejected(self):
        self.assertRejected(self.post(name="a" * 51), "name")

    def test_message_longer_than_1000_is_rejected(self):
        self.assertRejected(self.post(message="a" * 1001), "message")

    def test_max_lengths_are_accepted(self):
        self.assertRedirects(self.post(name="a" * 50, message="b" * 1000), self.url)
        self.assertEqual(GuestbookEntry.objects.count(), 1)

    def test_html_is_escaped(self):
        self.post(name="<b>x</b>", message="<script>alert('x')</script>")
        response = self.client.get(self.url)
        self.assertNotContains(response, "<script>alert")
        self.assertNotContains(response, "<b>x</b>")
        self.assertContains(response, "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;")
        self.assertContains(response, "&lt;b&gt;x&lt;/b&gt;")

    def test_entries_are_listed_newest_first(self):
        self.post(name="First")
        self.post(name="Second")
        content = self.client.get(self.url).content.decode()
        self.assertLess(content.index(">Second<"), content.index(">First<"))

    def test_post_requires_csrf_token(self):
        client = self.client_class(enforce_csrf_checks=True)
        response = client.post(self.url, {"name": "JB", "message": "Hello"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(GuestbookEntry.objects.count(), 0)


class GuestbookReplyTests(TestCase):
    def setUp(self):
        self.entry = GuestbookEntry.objects.create(name="Hong Gildong", message="Hello.")

    def reply_url(self, entry):
        return reverse("guestbook_reply", args=[entry.pk])

    def reply(self, entry, name="JB Kim", message="Thanks for visiting.", **extra):
        data = {"reply-name": name, "reply-message": message, **extra}
        return self.client.post(self.reply_url(entry), data)

    def assertReplyRejected(self, response, field):
        self.assertEqual(response.status_code, 200)
        self.assertIn(field, response.context["reply_form"].errors)
        self.assertContains(response, f'id="id_reply-{field}_error"')
        self.assertContains(response, "Reply to Hong Gildong")
        self.assertEqual(self.entry.replies.count(), 0)

    # Model / relationship

    def test_top_level_entry_has_no_parent(self):
        self.assertIsNone(self.entry.parent)

    def test_reply_has_parent_and_is_in_replies(self):
        reply = GuestbookEntry.objects.create(name="JB Kim", message="Hi", parent=self.entry)
        self.assertEqual(reply.parent, self.entry)
        self.assertEqual(list(self.entry.replies.all()), [reply])

    def test_nested_thread_is_stored_separately_from_other_entries(self):
        self.reply(self.entry, name="JB Kim", message="Reply 2")
        reply_2 = GuestbookEntry.objects.get(message="Reply 2")
        self.reply(reply_2, name="Hong Gildong", message="Reply 3")
        reply_3 = GuestbookEntry.objects.get(message="Reply 3")
        entry_4 = GuestbookEntry.objects.create(name="Kim Cheolsu", message="Entry 4")

        self.assertEqual(reply_2.parent, self.entry)
        self.assertEqual(reply_3.parent, reply_2)
        self.assertEqual(list(self.entry.replies.all()), [reply_2])
        self.assertEqual(list(reply_2.replies.all()), [reply_3])
        self.assertIsNone(entry_4.parent)
        self.assertFalse(entry_4.replies.exists())

    def test_deleting_an_entry_deletes_its_replies(self):
        reply = GuestbookEntry.objects.create(name="JB Kim", message="Reply", parent=self.entry)
        GuestbookEntry.objects.create(name="Hong Gildong", message="Reply 2", parent=reply)
        other = GuestbookEntry.objects.create(name="Kim Cheolsu", message="Other")
        self.entry.delete()
        self.assertEqual(list(GuestbookEntry.objects.all()), [other])

    # GET / POST

    def test_reply_page_opens_form_under_the_entry(self):
        response = self.client.get(self.reply_url(self.entry))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/guestbook.html")
        self.assertEqual(response.context["reply_to"], self.entry)
        self.assertContains(response, "Reply to Hong Gildong")
        self.assertContains(response, f'action="{self.reply_url(self.entry)}"')
        self.assertContains(response, 'id="id_reply-name"')
        self.assertContains(response, 'placeholder="Leave a reply"')
        self.assertContains(response, "csrfmiddlewaretoken", count=2)
        self.assertContains(response, f'href="/guestbook/#entry-{self.entry.pk}">Cancel</a>')
        self.assertContains(response, 'class="nav-link active" href="/guestbook/" aria-current="page"')

    def test_reply_post_saves_with_parent_and_redirects(self):
        response = self.reply(self.entry)
        reply = GuestbookEntry.objects.get(parent=self.entry)
        self.assertRedirects(response, f"/guestbook/#entry-{reply.pk}")
        self.assertEqual((reply.name, reply.message), ("JB Kim", "Thanks for visiting."))

    def test_reply_to_a_reply(self):
        self.reply(self.entry)
        jb_reply = GuestbookEntry.objects.get(parent=self.entry)
        response = self.reply(jb_reply, name="Hong Gildong", message="Thanks for the reply.")
        hong_reply = GuestbookEntry.objects.get(parent=jb_reply)
        self.assertRedirects(response, f"/guestbook/#entry-{hong_reply.pk}")
        self.assertEqual(hong_reply.name, "Hong Gildong")

    def test_reply_to_missing_entry_returns_404(self):
        missing = self.entry.pk + 100
        self.assertEqual(self.client.get(f"/guestbook/{missing}/reply/").status_code, 404)
        response = self.client.post(f"/guestbook/{missing}/reply/", {"reply-name": "A", "reply-message": "B"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(GuestbookEntry.objects.count(), 1)

    def test_invalid_reply_id_returns_404(self):
        self.assertEqual(self.client.get("/guestbook/abc/reply/").status_code, 404)
        self.assertEqual(self.client.post("/guestbook/-1/reply/", {}).status_code, 404)

    def test_parent_in_post_body_is_ignored(self):
        other = GuestbookEntry.objects.create(name="Kim Cheolsu", message="Other")
        self.reply(self.entry, **{"parent": other.pk, "reply-parent": other.pk})
        reply = GuestbookEntry.objects.get(message="Thanks for visiting.")
        self.assertEqual(reply.parent, self.entry)
        self.assertFalse(other.replies.exists())

    def test_empty_reply_name_is_rejected(self):
        self.assertReplyRejected(self.reply(self.entry, name=""), "name")

    def test_empty_reply_message_is_rejected(self):
        self.assertReplyRejected(self.reply(self.entry, message=""), "message")

    def test_reply_name_longer_than_50_is_rejected(self):
        self.assertReplyRejected(self.reply(self.entry, name="a" * 51), "name")

    def test_reply_message_longer_than_1000_is_rejected(self):
        self.assertReplyRejected(self.reply(self.entry, message="a" * 1001), "message")

    def test_reply_requires_csrf_token(self):
        client = self.client_class(enforce_csrf_checks=True)
        response = client.post(self.reply_url(self.entry), {"reply-name": "JB", "reply-message": "Hi"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.entry.replies.exists())

    def test_korean_text_round_trip(self):
        self.client.post("/guestbook/", {"name": "홍길동", "message": "안녕하세요."})
        root = GuestbookEntry.objects.get(name="홍길동", parent=None)
        self.reply(root, name="김철수", message="답변 감사합니다.")
        reply = GuestbookEntry.objects.get(parent=root)
        self.assertEqual((reply.name, reply.message), ("김철수", "답변 감사합니다."))
        response = self.client.get("/guestbook/")
        self.assertContains(response, "안녕하세요.")
        self.assertContains(response, "답변 감사합니다.")

    def test_reply_html_is_escaped(self):
        self.reply(self.entry, name="<i>JB</i>", message="<script>alert('XSS')</script>")
        response = self.client.get("/guestbook/")
        self.assertNotContains(response, "<script>alert")
        self.assertNotContains(response, "<i>JB</i>")
        self.assertContains(response, "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;")
        self.assertContains(response, "&lt;i&gt;JB&lt;/i&gt;")

    # Display

    def test_threads_keep_replies_under_their_own_entry(self):
        self.reply(self.entry, message="First answer")
        first_answer = GuestbookEntry.objects.get(message="First answer")
        self.reply(first_answer, name="Hong Gildong", message="Thanks for the reply.")
        second = GuestbookEntry.objects.create(name="Kim Cheolsu", message="Second post")
        self.reply(second, message="Second answer")

        response = self.client.get("/guestbook/")
        threads = [
            (entry.message, [(reply.message, reply.depth) for reply in replies])
            for entry, replies in response.context["threads"]
        ]
        self.assertEqual(threads, [
            ("Second post", [("Second answer", 1)]),
            ("Hello.", [("First answer", 1), ("Thanks for the reply.", 2)]),
        ])
        content = response.content.decode()
        first_block = content[content.index(f'id="entry-{self.entry.pk}"'):]
        second_block = content[content.index(f'id="entry-{second.pk}"'):content.index(f'id="entry-{self.entry.pk}"')]
        self.assertIn("First answer", first_block)
        self.assertNotIn("Second answer", first_block)
        self.assertIn("Second answer", second_block)
        self.assertNotIn("First answer", second_block)
        self.assertContains(response, 'class="guestbook-reply guestbook-reply-indent-2"')

    def test_replies_are_listed_oldest_first_within_a_thread(self):
        for message in ["Reply A", "Reply B", "Reply C"]:
            self.reply(self.entry, message=message)
        replies = self.client.get("/guestbook/").context["threads"][0][1]
        self.assertEqual([reply.message for reply in replies], ["Reply A", "Reply B", "Reply C"])

    def test_deep_replies_are_capped_and_labelled(self):
        parent = self.entry
        for depth in range(1, 5):
            parent = GuestbookEntry.objects.create(name=f"Level {depth}", message=f"Depth {depth}", parent=parent)
        response = self.client.get("/guestbook/")
        replies = response.context["threads"][0][1]
        self.assertEqual([(r.depth, r.indent) for r in replies], [(1, 1), (2, 2), (3, 3), (4, 3)])
        self.assertContains(response, "Replying to Level 3", count=1)

    def test_reply_links_are_shown_for_entries_and_replies(self):
        reply = GuestbookEntry.objects.create(name="JB Kim", message="Hi", parent=self.entry)
        response = self.client.get("/guestbook/")
        for entry in [self.entry, reply]:
            with self.subTest(entry=entry.name):
                self.assertContains(response, f'href="{self.reply_url(entry)}#reply-form" aria-label="Reply to {entry.name}"')
        self.assertNotContains(response, 'id="reply-form"')

    def test_guestbook_page_uses_a_single_query(self):
        reply = GuestbookEntry.objects.create(name="JB Kim", message="Hi", parent=self.entry)
        GuestbookEntry.objects.create(name="Hong Gildong", message="Hi again", parent=reply)
        with self.assertNumQueries(1):
            self.client.get("/guestbook/")

    def test_admin_changelist_shows_parent(self):
        GuestbookEntry.objects.create(name="JB Kim", message="Hi", parent=self.entry)
        admin_user = get_user_model().objects.create_superuser("admin", "", "pass")
        self.client.force_login(admin_user)
        response = self.client.get("/admin/pages/guestbookentry/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "column-parent")
        replies_only = self.client.get("/admin/pages/guestbookentry/?parent__isempty=0")
        self.assertEqual([e.name for e in replies_only.context["cl"].result_list], ["JB Kim"])


VIBE_ARTIST_URL = "https://vibe.naver.com/artist/499481"
KYOBO_AUTHOR_URL = "https://store.kyobobook.co.kr/person/detail/1122019501"


class CreativeWorksTests(TestCase):
    # VIBE

    def test_vibe_albums_are_listed_newest_first_without_network(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            works = creative_works.creative_works()
        urlopen.assert_not_called()
        self.assertEqual([(i["title"], i["subtitle"], i["url"]) for i in works["albums"]["items"]], [
            ("On The Start Line", "2022-05-03", "https://vibe.naver.com/album/7522961"),
            ("Enjoy Your Memory", "2022-02-04", "https://vibe.naver.com/album/7095471"),
            ("대한의 딸들", "2021-07-01", "https://vibe.naver.com/album/6101773"),
        ])
        self.assertEqual(works["vibe_artist_url"], VIBE_ARTIST_URL)
        self.assertEqual(works["kyobo_author_url"], KYOBO_AUTHOR_URL)

    def test_vibe_links_and_covers_are_https_on_vibe_hosts(self):
        items = creative_works.vibe_albums()
        self.assertEqual(len(items), 3)
        for item in items:
            with self.subTest(url=item["url"]):
                for url in (item["url"], item["image"]):
                    parts = urllib.parse.urlsplit(url)
                    self.assertEqual(parts.scheme, "https")
                    self.assertIn(parts.hostname, creative_works.VIBE_HOSTS)
        self.assertEqual(
            items[0]["image"],
            "https://musicmeta-phinf.pstatic.net/album/007/522/7522961.jpg?type=r480Fll&v=20230331101518",
        )

    def test_vibe_artist_url_uses_configured_id(self):
        self.assertEqual(creative_works.vibe_artist_url(), VIBE_ARTIST_URL)
        with override_settings(VIBE_ARTIST_ID="42"):
            self.assertEqual(creative_works.vibe_artist_url(), "https://vibe.naver.com/artist/42")

    def test_vibe_list_is_capped_and_unsafe_covers_are_dropped(self):
        extra = [
            ("New Album", "2027-02-01", "1", "https://musicmeta-phinf.pstatic.net/album/1.jpg"),
            ("Bad Cover", "2027-01-01", "2", "https://evil.example/x.jpg"),
        ]
        with mock.patch.object(creative_works, "VIBE_ALBUMS", creative_works.VIBE_ALBUMS + extra):
            items = creative_works.vibe_albums()
        self.assertEqual([i["title"] for i in items], ["New Album", "Bad Cover", "On The Start Line"])
        self.assertEqual(items[1]["image"], "")
        self.assertEqual(items[1]["url"], "https://vibe.naver.com/album/2")

    def test_safe_url_rejects_other_schemes_and_hosts(self):
        hosts = creative_works.VIBE_HOSTS
        self.assertEqual(creative_works.safe_url("javascript:alert(1)", hosts), "")
        self.assertEqual(creative_works.safe_url("https://example.com/album/1", hosts), "")
        self.assertEqual(creative_works.safe_url("https://vibe.naver.com.evil.example/", hosts), "")
        self.assertEqual(creative_works.safe_url("http://vibe.naver.com/album/1#x", hosts), "https://vibe.naver.com/album/1")

    # Kyobo

    def test_kyobo_books_are_listed_newest_first(self):
        self.assertEqual([(i["title"], i["subtitle"]) for i in creative_works.kyobo_books()], [
            ("래퍼의 노트", "eBook · 바른북스 · 2026-09-08"),
            ("래퍼의 노트", "바른북스 · 2026-08-25"),
        ])

    def test_kyobo_links_and_covers_are_https_on_kyobo_hosts(self):
        for item in creative_works.kyobo_books():
            with self.subTest(url=item["url"]):
                for url in (item["url"], item["image"]):
                    parts = urllib.parse.urlsplit(url)
                    self.assertEqual(parts.scheme, "https")
                    self.assertIn(parts.hostname, creative_works.KYOBO_HOSTS)
        urls = [i["url"] for i in creative_works.kyobo_books()]
        self.assertEqual(urls, [
            "https://ebook-product.kyobobook.co.kr/dig/epd/ebook/E000013555457",
            "https://product.kyobobook.co.kr/detail/S000220995923",
        ])

    def test_kyobo_author_url_uses_configured_id(self):
        self.assertEqual(creative_works.kyobo_author_url(), KYOBO_AUTHOR_URL)
        with override_settings(KYOBO_AUTHOR_ID="42"):
            self.assertEqual(creative_works.kyobo_author_url(), "https://store.kyobobook.co.kr/person/detail/42")

    def test_kyobo_list_is_capped_and_unsafe_entries_are_dropped(self):
        extra = [
            ("Book A", "", "Press", "2027-01-01", "https://product.kyobobook.co.kr/detail/S1", ""),
            ("Book B", "", "Press", "2027-02-01", "https://product.kyobobook.co.kr/detail/S2", ""),
            ("Evil", "", "Press", "2027-03-01", "javascript:alert(1)", ""),
            ("Elsewhere", "", "Press", "2027-04-01", "https://example.com/book", ""),
        ]
        with mock.patch.object(creative_works, "KYOBO_BOOKS", creative_works.KYOBO_BOOKS + extra):
            titles = [i["title"] for i in creative_works.kyobo_books()]
        self.assertEqual(titles, ["Book B", "Book A", "래퍼의 노트"])

    # Home page

    def test_home_music_links_to_vibe(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<h3 id="creative-works-heading" class="card-title text-title">Creative Works</h3>',
            html=True,
        )
        for title in ["On The Start Line", "Enjoy Your Memory", "대한의 딸들"]:
            with self.subTest(title=title):
                self.assertContains(response, f'aria-label="Listen on VIBE: {title}">Listen on VIBE</a>')
        self.assertContains(response, ">Listen on VIBE</a>", count=3)
        self.assertContains(response, 'href="https://vibe.naver.com/album/7522961" target="_blank" rel="noopener noreferrer"')
        self.assertContains(
            response,
            f'class="button-primary creative-works-more" href="{VIBE_ARTIST_URL}" target="_blank" rel="noopener noreferrer">View All on VIBE</a>',
        )
        self.assertContains(response, 'src="https://musicmeta-phinf.pstatic.net/album/007/522/7522961.jpg?type=r480Fll&amp;v=20230331101518"')
        self.assertContains(response, 'class="creative-work-cover creative-work-cover-square"', count=3)
        self.assertContains(response, 'onerror="this.remove()"', count=5)
        self.assertNotContains(response, "spotify")
        self.assertNotContains(response, "Spotify")

    def test_home_escapes_curated_titles(self):
        with mock.patch.object(creative_works, "VIBE_ALBUMS", [("New <b>Album</b>", "2027-01-01", "1", "")]):
            response = self.client.get("/")
        self.assertContains(response, "New &lt;b&gt;Album&lt;/b&gt;")
        self.assertNotContains(response, "New <b>Album</b>")

    def test_home_books_link_to_kyobo(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ">View on Kyobo</a>", count=2)
        self.assertContains(
            response,
            f'href="{KYOBO_AUTHOR_URL}" target="_blank" rel="noopener noreferrer">View All on Kyobo</a>',
        )
        self.assertContains(response, 'href="https://product.kyobobook.co.kr/detail/S000220995923"')
        self.assertContains(response, 'src="https://contents.kyobobook.co.kr/sih/fit-in/300x0/pdt/9791176214476.jpg"', count=2)
        self.assertContains(response, 'class="creative-work-cover creative-work-cover-book"', count=2)
        self.assertNotContains(response, "aladin")
        self.assertNotContains(response, "Aladin")

    def test_home_survives_a_broken_list(self):
        with mock.patch.object(creative_works, "VIBE_ALBUMS", [("only a title",)]):
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New music is coming soon.")
        self.assertContains(response, ">View All on VIBE</a>")
