"""YouTube videos on announcements, news posts and events.

The add / edit forms have a "YouTube video link" box (name="video_url").
Only real YouTube links are accepted; we keep just the link and take the
11-character video ID out of it. The public site then builds the player
itself (youtube-nocookie.com, the privacy-enhanced mode), so nobody can put
other website code on the page.

Accepted links:
    https://www.youtube.com/watch?v=ID   (also m.youtube.com, &t=..., &list=...)
    https://youtu.be/ID
    https://www.youtube.com/shorts/ID
    https://www.youtube.com/live/ID
    https://www.youtube.com/embed/ID
"""
import re
from urllib.parse import parse_qs, urlparse

_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
          "youtube-nocookie.com", "www.youtube-nocookie.com"}


def youtube_id(url):
    """The video ID of a YouTube link, or "" when it isn't one."""
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    try:
        u = urlparse(url)
    except ValueError:
        return ""
    host = (u.hostname or "").lower()
    path = u.path or ""
    vid = ""
    if host in ("youtu.be", "www.youtu.be"):
        vid = path.lstrip("/").split("/")[0]
    elif host in _HOSTS:
        if path == "/watch":
            vid = (parse_qs(u.query).get("v") or [""])[0]
        else:
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 2 and parts[0] in ("shorts", "live", "embed", "v"):
                vid = parts[1]
    return vid if _ID.match(vid or "") else ""


def clean_video_url(raw):
    """(link to save, problem). An empty box removes the video."""
    raw = (raw or "").strip()
    if not raw:
        return "", None
    vid = youtube_id(raw)
    if not vid:
        return None, ("The video link was not saved: please paste a YouTube link, "
                      "e.g. https://www.youtube.com/watch?v=… or https://youtu.be/…")
    return f"https://www.youtube.com/watch?v={vid}", None


def save_video(request, obj):
    """Called from content_photos.save_content_photos (every add / edit of an
    announcement, news post or event). Returns a list of problems."""
    if "video_url" not in request.POST:
        return []          # this form has no video box: leave the video as it is
    link, problem = clean_video_url(request.POST.get("video_url"))
    if problem:
        return [problem]
    if link != (obj.video_url or ""):
        obj.video_url = link
        type(obj).objects.filter(pk=obj.pk).update(video_url=link)
    return []