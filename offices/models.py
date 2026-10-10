from django.db import models

class Office(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, max_length=150)

    logo = models.ImageField(upload_to="office_logos/", blank=True, null=True)
    about = models.TextField(blank=True)
    description = models.TextField(blank=True)
    head_name = models.CharField(max_length=255, blank=True)
    position_title = models.CharField(max_length=255, blank=True)
    office_hours = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    telephone = models.CharField(max_length=100, blank=True)

    # These six are optional ("if applicable") — not every office has a
    # formal mandate/vision/etc., so they're left blank rather than required.
    service_pledge = models.TextField(blank=True)
    mandate = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    mission = models.TextField(blank=True)
    goal = models.TextField(blank=True)
    objective = models.TextField(blank=True)

    facebook_url = models.URLField(
        blank=True,
        help_text="Link to this office's official Facebook page, shown as an icon on its public page.",
    )

    twitter_url = models.URLField(
        blank=True,
        help_text="Link to this office's official X (Twitter) page, shown as an icon on its public page.",
    )
    instagram_url = models.URLField(
        blank=True,
        help_text="Link to this office's official Instagram page, shown as an icon on its public page.",
    )
    youtube_url = models.URLField(
        blank=True,
        help_text="Link to this office's official YouTube channel, shown as an icon on its public page.",
    )

    # The account / page names shown next to the social media icons on the
    # public office page (e.g. "Tunga Mayor's Office"). Optional — when blank,
    # a name is taken from the link itself (see social_links below).
    facebook_name = models.CharField(max_length=100, blank=True)
    twitter_name = models.CharField(max_length=100, blank=True)
    instagram_name = models.CharField(max_length=100, blank=True)
    youtube_name = models.CharField(max_length=100, blank=True)

    hero_image = models.ImageField(
        upload_to="office_hero/",
        blank=True,
        null=True,
        help_text="Banner image shown at the top of this office's public page. Defaults to the standard municipal hall photo when empty.",
    )

    # Position on the public site (Offices page, navbar dropdown, directory):
    # lower numbers come first. The Super Admin sets this by dragging offices
    # on the Office Overview page. New offices default to the end of the list.
    display_order = models.PositiveIntegerField(default=9999)

    is_visible = models.BooleanField(
        default=True,
        help_text="Uncheck to hide this office from the public Offices page."
    )

    # ---- social media (public office page) ---------------------------------
    SOCIAL_PLATFORMS = [
        # field prefix, platform name, icon
        ("facebook", "Facebook", "fa-brands fa-facebook"),
        ("twitter", "X (Twitter)", "fa-brands fa-x-twitter"),
        ("instagram", "Instagram", "fa-brands fa-instagram"),
        ("youtube", "YouTube", "fa-brands fa-youtube"),
    ]

    @staticmethod
    def account_name_from_url(url, handle=False):
        """A readable account name taken from a social media link, e.g.
        facebook.com/TungaMayorsOffice -> "TungaMayorsOffice",
        youtube.com/@TungaLGU -> "@TungaLGU", instagram.com/tunga.mayor (handle=True)
        -> "@tunga.mayor". "" when the link has no name in it (a number ID or a
        YouTube channel code) — then the office's own name is shown instead."""
        from urllib.parse import urlparse, unquote
        try:
            parts = [unquote(p) for p in urlparse(url or "").path.split("/") if p]
        except ValueError:
            return ""
        if not parts:
            return ""
        first = parts[0].lower()
        if first in ("channel", "profile.php") or parts[0].isdigit():
            return ""                                   # only an ID, no name
        if first in ("pages", "pg", "people", "c", "user", "groups") and len(parts) > 1:
            parts = parts[1:]
        name = parts[0]
        if name.startswith("@"):
            return name
        if handle:
            return "@" + name
        return name.replace("-", " ").replace("_", " ").strip()

    @property
    def social_links(self):
        """The office's social media accounts that have a link, each with its
        icon, platform name and account name — used by offices/office_detail.html."""
        links = []
        for key, platform, icon in self.SOCIAL_PLATFORMS:
            url = getattr(self, f"{key}_url", "")
            if not url:
                continue
            name = ((getattr(self, f"{key}_name", "") or "").strip()
                    or self.account_name_from_url(url, handle=key in ("twitter", "instagram"))
                    or self.name)
            links.append({"key": key, "url": url, "platform": platform, "icon": icon, "name": name})
        return links

    def __str__(self):
        return self.name