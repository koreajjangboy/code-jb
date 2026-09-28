from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import GuestbookEntryForm
from .models import GuestbookEntry, Project

# Replies deeper than this are drawn at this indentation level (with a "Replying to" label).
MAX_REPLY_INDENT = 3


def home(request):
    return render(request, "pages/home.html")


def about(request):
    return render(request, "pages/about.html")


def projects(request):
    projects = Project.objects.filter(is_published=True)
    return render(
        request,
        "pages/projects.html",
        {"projects": projects},
    )


def guestbook_threads():
    """Top-level entries, newest first, each with its replies in conversation order.

    Loads every entry in one query and returns [(entry, [reply, ...]), ...]; each reply
    gets ``depth`` (1 = direct reply) and ``indent`` (depth capped at MAX_REPLY_INDENT).
    """
    children = {}
    for entry in GuestbookEntry.objects.select_related("parent").order_by("created_at", "id"):
        children.setdefault(entry.parent_id, []).append(entry)

    threads = []
    for root in reversed(children.get(None, [])):
        replies = []
        stack = [(child, 1) for child in reversed(children.get(root.pk, []))]
        while stack:
            reply, depth = stack.pop()
            reply.depth = depth
            reply.indent = min(depth, MAX_REPLY_INDENT)
            replies.append(reply)
            stack.extend((child, depth + 1) for child in reversed(children.get(reply.pk, [])))
        threads.append((root, replies))
    return threads


def render_guestbook(request, form, reply_to=None, reply_form=None):
    return render(
        request,
        "pages/guestbook.html",
        {
            "form": form,
            "threads": guestbook_threads(),
            "reply_to": reply_to,
            "reply_form": reply_form,
        },
    )


def guestbook(request):
    if request.method == "POST":
        form = GuestbookEntryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("guestbook")
    else:
        form = GuestbookEntryForm()
    return render_guestbook(request, form)


def guestbook_reply(request, entry_id):
    parent = get_object_or_404(GuestbookEntry, pk=entry_id)
    # The parent comes only from the URL; the form itself accepts just name and message.
    reply_form = GuestbookEntryForm(request.POST or None, prefix="reply")
    reply_form.fields["message"].widget.attrs["placeholder"] = "Leave a reply"
    reply_form.fields["name"].widget.attrs["autofocus"] = True
    if request.method == "POST" and reply_form.is_valid():
        reply = reply_form.save(commit=False)
        reply.parent = parent
        reply.save()
        return redirect(f"{reverse('guestbook')}#entry-{reply.pk}")
    return render_guestbook(request, GuestbookEntryForm(), reply_to=parent, reply_form=reply_form)