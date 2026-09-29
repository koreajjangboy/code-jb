"""Latest music (Spotify Web API) and books (Kyobo Book Centre links) for the home page.

Every public function here is safe to call from a view: missing credentials, network errors,
bad responses and unexpected data all end in fallback content instead of an exception.

Kyobo has no public book API, so books are a curated list (KYOBO_BOOKS) with Kyobo product links.

Caching (Django cache):
- a successful result is kept for CREATIVE_WORKS_CACHE_SECONDS (24 h);
- after a failure the fallback is kept for FAILURE_CACHE_SECONDS, so the APIs are not retried
  on every request;
- the last successful result is also kept for STALE_CACHE_SECONDS and shown during failures.
"""
import base64
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 4
FAILURE_CACHE_SECONDS = 60 * 10
STALE_CACHE_SECONDS = 60 * 60 * 24 * 30
MAX_ITEMS = 3

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_ALBUMS_URL = "https://api.spotify.com/v1/artists/{artist_id}/albums"

SPOTIFY_LINK_HOSTS = {"open.spotify.com"}
SPOTIFY_IMAGE_HOSTS = {"i.scdn.co", "mosaic.scdn.co", "image-cdn-ak.spotifycdn.com", "image-cdn-fa.spotifycdn.com"}
KYOBO_HOSTS = {"store.kyobobook.co.kr", "product.kyobobook.co.kr", "ebook-product.kyobobook.co.kr", "contents.kyobobook.co.kr"}


class CreativeWorksError(Exception):
    """Any problem while fetching or parsing an external API response."""


def safe_url(url, allowed_hosts):
    """Return ``url`` as https if its host is allowed, else "" (never pass API URLs through blindly)."""
    try:
        parts = urlsplit(str(url or "").strip())
    except ValueError:
        return ""
    if parts.scheme not in ("http", "https") or parts.hostname not in allowed_hosts:
        return ""
    return urlunsplit(("https", parts.netloc, parts.path, parts.query, ""))


def fetch_json(url, *, data=None, headers=None):
    request = urllib.request.Request(url, data=data, headers={"Accept": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise CreativeWorksError(f"request failed: {error}") from error
    try:
        # strict=False tolerates unescaped control characters that some APIs emit.
        return json.loads(body.decode("utf-8"), strict=False)
    except (UnicodeDecodeError, ValueError) as error:
        raise CreativeWorksError("response is not valid JSON") from error


def cached(key, loader, fallback):
    """Return cached data for ``key``; on a miss call ``loader`` and cache the outcome."""
    result = cache.get(key)
    if result is not None:
        return result
    try:
        items = loader()
        if not items:
            raise CreativeWorksError("no items in response")
    except CreativeWorksError as error:
        logger.warning("creative works: %s unavailable (%s)", key, error)
        stale = cache.get(f"{key}:last-good")
        result = stale if stale is not None else {"items": fallback(), "is_fallback": True}
        cache.set(key, result, FAILURE_CACHE_SECONDS)
        return result
    except Exception:  # never let an unexpected API shape break the home page
        logger.exception("creative works: unexpected error for %s", key)
        result = {"items": fallback(), "is_fallback": True}
        cache.set(key, result, FAILURE_CACHE_SECONDS)
        return result
    result = {"items": items, "is_fallback": False}
    cache.set(key, result, settings.CREATIVE_WORKS_CACHE_SECONDS)
    cache.set(f"{key}:last-good", result, STALE_CACHE_SECONDS)
    return result


# Spotify

def spotify_artist_url():
    return f"https://open.spotify.com/artist/{settings.SPOTIFY_ARTIST_ID}"


# Newest releases as listed on the public Spotify artist page (checked 2026-09-29).
FALLBACK_ALBUMS = [
    ("On The Start Line", "2022-04-26", "2vekOtXT4CxRwTts40BAo3", "ab67616d0000b273c5fa0789cbf0ae3cc093154b"),
    ("Enjoy Your Memory", "2022-01-25", "6RAt0wAHVY2UngL9sj2VL6", "ab67616d0000b2738138944cf6a88d35a6564757"),
    ("Daehan's Daughters", "2021-06-22", "1UYlbt8Rg5UcZKSXbF6rsz", "ab67616d0000b273675cd8182bc8c696ed6dc18a"),
]


def spotify_fallback():
    return [
        {
            "title": title,
            "subtitle": f"Single · {date}",
            "image": f"https://i.scdn.co/image/{image}",
            "url": f"https://open.spotify.com/album/{album_id}",
        }
        for title, date, album_id, image in FALLBACK_ALBUMS[:MAX_ITEMS]
    ]


def spotify_token():
    token = cache.get("creative_works:spotify:token")
    if token:
        return token
    credentials = f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}".encode()
    data = fetch_json(
        SPOTIFY_TOKEN_URL,
        data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        headers={
            "Authorization": "Basic " + base64.b64encode(credentials).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    token = data.get("access_token") if isinstance(data, dict) else None
    if not token:
        raise CreativeWorksError("Spotify did not return an access token")
    expires_in = int(data.get("expires_in") or 3600)
    cache.set("creative_works:spotify:token", token, max(60, expires_in - 60))
    return token


def load_spotify_albums():
    if not (settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET):
        raise CreativeWorksError("Spotify credentials are not configured")
    query = urllib.parse.urlencode({"include_groups": "album,single", "market": "KR", "limit": 10})
    url = SPOTIFY_ALBUMS_URL.format(artist_id=urllib.parse.quote(settings.SPOTIFY_ARTIST_ID)) + "?" + query
    data = fetch_json(url, headers={"Authorization": f"Bearer {spotify_token()}"})
    albums = data.get("items") if isinstance(data, dict) else None
    if not isinstance(albums, list):
        raise CreativeWorksError(f"unexpected Spotify response: {data.get('error') if isinstance(data, dict) else data!r}")

    items, seen = [], set()
    # release_date may be "YYYY", "YYYY-MM" or "YYYY-MM-DD"; string order works for newest-first.
    for album in sorted((a for a in albums if isinstance(a, dict)), key=lambda a: str(a.get("release_date", "")), reverse=True):
        title = str(album.get("name") or "").strip()
        url = safe_url((album.get("external_urls") or {}).get("spotify"), SPOTIFY_LINK_HOSTS)
        if not title or not url or title.lower() in seen:
            continue
        seen.add(title.lower())
        images = [i for i in album.get("images") or [] if isinstance(i, dict)]
        image = min(images, key=lambda i: abs((i.get("width") or 300) - 300), default={}).get("url")
        kind = {"album": "Album", "single": "Single", "compilation": "Compilation"}.get(album.get("album_type"), "Release")
        items.append({
            "title": title,
            "subtitle": " · ".join(part for part in (kind, str(album.get("release_date") or "")) if part),
            "image": safe_url(image, SPOTIFY_IMAGE_HOSTS),
            "url": url,
        })
        if len(items) == MAX_ITEMS:
            break
    return items


def latest_albums():
    return cached("creative_works:spotify:albums", load_spotify_albums, spotify_fallback)


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
    items = []
    for title, edition, publisher, date, url, image in sorted(KYOBO_BOOKS, key=lambda b: b[3], reverse=True):
        url = safe_url(url, KYOBO_HOSTS)
        if not url:
            continue
        items.append({
            "title": title,
            "subtitle": " · ".join(part for part in (edition, publisher, date) if part),
            "image": safe_url(image, KYOBO_HOSTS),
            "url": url,
        })
    return items[:MAX_ITEMS]


def latest_books():
    # A local list: no network call, so nothing to cache and nothing that can fail.
    return {"items": kyobo_books(), "is_fallback": False}


def creative_works():
    """Context for the home page. Never raises."""
    try:
        albums, books = latest_albums(), latest_books()
    except Exception:  # e.g. the cache backend itself failing
        logger.exception("creative works: falling back completely")
        albums = {"items": spotify_fallback(), "is_fallback": True}
        books = {"items": kyobo_books(), "is_fallback": False}
    return {
        "albums": albums,
        "books": books,
        "spotify_artist_url": spotify_artist_url(),
        "kyobo_author_url": kyobo_author_url(),
    }
