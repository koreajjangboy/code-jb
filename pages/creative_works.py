"""Latest music (Naver VIBE links) and books (Kyobo Book Centre links) for the home page.

Neither VIBE nor Kyobo offers a public API (and apis.naver.com disallows automated access in
robots.txt), so both are curated lists with links to the official pages. Nothing here touches
the network, so there is nothing to cache and nothing that can time out.

Every URL still goes through safe_url(), so a typo in a list can never put a non-https or
off-site link on the page: such an entry is dropped instead.
"""
import logging
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings

logger = logging.getLogger(__name__)

MAX_ITEMS = 3

VIBE_HOSTS = {"vibe.naver.com", "musicmeta-phinf.pstatic.net", "music-phinf.pstatic.net"}
KYOBO_HOSTS = {"store.kyobobook.co.kr", "product.kyobobook.co.kr", "ebook-product.kyobobook.co.kr", "contents.kyobobook.co.kr"}


def safe_url(url, allowed_hosts):
    """Return ``url`` as https if its host is allowed, else ""."""
    try:
        parts = urlsplit(str(url or "").strip())
    except ValueError:
        return ""
    if parts.scheme not in ("http", "https") or parts.hostname not in allowed_hosts:
        return ""
    return urlunsplit(("https", parts.netloc, parts.path, parts.query, ""))


def curated(entries, allowed_hosts):
    """Newest-first items from (title, subtitle parts, date, url, image) tuples, unsafe links dropped."""
    items = []
    for title, parts, date, url, image in sorted(entries, key=lambda e: e[2], reverse=True):
        url = safe_url(url, allowed_hosts)
        if not url:
            continue
        items.append({
            "title": title,
            "subtitle": " · ".join(part for part in (*parts, date) if part),
            "image": safe_url(image, allowed_hosts),
            "url": url,
        })
    return items[:MAX_ITEMS]


# VIBE

def vibe_artist_url():
    return f"https://vibe.naver.com/artist/{settings.VIBE_ARTIST_ID}"


# Newest releases on the VIBE artist page (checked 2026-10-02). Update this list when new music is out.
# (title, release date, VIBE album id, cover image URL)
VIBE_ALBUMS = [
    (
        "On The Start Line", "2022-05-03", "7522961",
        "https://musicmeta-phinf.pstatic.net/album/007/522/7522961.jpg?type=r480Fll&v=20230331101518",
    ),
    (
        "Enjoy Your Memory", "2022-02-04", "7095471",
        "https://musicmeta-phinf.pstatic.net/album/007/095/7095471.jpg?type=r480Fll&v=20230331105931",
    ),
    (
        "대한의 딸들", "2021-07-01", "6101773",
        "https://musicmeta-phinf.pstatic.net/album/006/101/6101773.jpg?type=r480Fll&v=20230331123830",
    ),
]


def vibe_albums():
    return curated(
        [(title, (), date, f"https://vibe.naver.com/album/{album_id}", image)
         for title, date, album_id, image in VIBE_ALBUMS],
        VIBE_HOSTS,
    )


# Kyobo

def kyobo_author_url():
    return f"https://store.kyobobook.co.kr/person/detail/{settings.KYOBO_AUTHOR_ID}"


# Checked on the Kyobo author page (2026-09-29). Update this list when a new book is published.
# (title, edition, publisher, publication date, product URL, cover image URL)
KYOBO_BOOKS = [
    (
        "래퍼의 노트", "eBook", "바른북스", "2026-09-08",
        "https://ebook-product.kyobobook.co.kr/dig/epd/ebook/E000013555457",
        "https://contents.kyobobook.co.kr/sih/fit-in/300x0/pdt/9791176214476.jpg",
    ),
    (
        "래퍼의 노트", "", "바른북스", "2026-08-25",
        "https://product.kyobobook.co.kr/detail/S000220995923",
        "https://contents.kyobobook.co.kr/sih/fit-in/300x0/pdt/9791176214476.jpg",
    ),
]


def kyobo_books():
    return curated(
        [(title, (edition, publisher), date, url, image)
         for title, edition, publisher, date, url, image in KYOBO_BOOKS],
        KYOBO_HOSTS,
    )


def creative_works():
    """Context for the home page. Never raises."""
    try:
        albums, books = vibe_albums(), kyobo_books()
    except Exception:  # e.g. a malformed entry in one of the lists
        logger.exception("creative works: could not build the lists")
        albums, books = [], []
    return {
        "albums": {"items": albums},
        "books": {"items": books},
        "vibe_artist_url": vibe_artist_url(),
        "kyobo_author_url": kyobo_author_url(),
    }
