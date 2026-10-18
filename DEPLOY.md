# Deploying the Tunga Portal (DigitalOcean + Namecheap domain)

There are two ways. Pick one:

| | **A. App Platform** (recommended) | **B. Droplet** (a virtual server) |
|---|---|---|
| Setup | Click-through, no server to manage | One script on the server |
| Updates | Automatic on every `git push` | Run `deploy/update.sh` |
| Database | Managed by DigitalOcean | PostgreSQL on the Droplet |
| Uploaded photos/PDFs | Cloudinary or Spaces | The Droplet's disk (or Cloudinary) |
| Files used | `.do/app.yaml`, `Procfile`, `gunicorn.conf.py` | `deploy/setup_droplet.sh`, `deploy/update.sh` |

Both use the same settings (all listed in `.env.example`).

---

## Before you start (both ways)

1. **Put the code on GitHub** (private repository is fine). Never upload
   `.env`, `db.sqlite3`, `media/` or `private_backups/` — `.gitignore` already
   leaves them out.
2. **Make the secret values** on your computer (keep them somewhere safe):
   ```
   python -c "import secrets; print(secrets.token_urlsafe(50))"                               # SECRET_KEY
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"   # OTP_ENCRYPTION_KEY
   ```
   Use the **same OTP_ENCRYPTION_KEY** as on Render if you are moving the site,
   otherwise the saved email-provider keys can't be read (you would just type them again).
3. **Moving from Render?** On the old site: Super Admin → Backup & Restore →
   make a full backup → Download. After the new site is up, restore it there.

---

## A. DigitalOcean App Platform

1. Open `.do/app.yaml` and change the lines marked `<-- CHANGE`
   (your GitHub repository and your domain). Commit and push.
2. DigitalOcean → **Create → Apps** → GitHub → choose the repository → finish.
3. Your app → **Settings → App Spec → Edit** → paste the whole `.do/app.yaml`
   → **Save**. This adds the PostgreSQL database, the setup job and the domain.
4. Your app → **Settings → Environment Variables (App-Level)**: replace every
   `CHANGE-ME` (SECRET_KEY, OTP_ENCRYPTION_KEY, ADMIN_URL, Cloudinary keys,
   reCAPTCHA keys, first superuser). Save → the app deploys.
5. Each deploy runs, in order: install packages → `collectstatic` →
   **setup job** (`migrate` + `setup_production`) → start the website.
   Check **Activity → Deploy logs**; `setup_production` lists any missing setting.
6. Open the free address (`https://<name>.ondigitalocean.app`) to test.

### Connect the Namecheap domain (App Platform)

Easiest — let DigitalOcean manage the DNS:
1. Namecheap → Domain List → **Manage** → Nameservers → **Custom DNS**:
   `ns1.digitalocean.com`, `ns2.digitalocean.com`, `ns3.digitalocean.com` → ✓.
2. DigitalOcean → your app → **Settings → Domains**: the domain from app.yaml is
   listed; choose "We manage your domain". HTTPS is added automatically.

Or keep Namecheap DNS: Namecheap → Advanced DNS, add
* `CNAME` — host `www` — value `<name>.ondigitalocean.app.`
* `ALIAS` — host `@` — value `<name>.ondigitalocean.app.`

DNS changes take from a few minutes up to 24 hours.

> Uploaded files: App Platform's own disk is erased on every deploy, so keep
> `MEDIA_STORAGE=cloudinary` (or `spaces`). Backups made in Super Admin are
> kept only when Spaces is used — otherwise download each backup.

---

## B. DigitalOcean Droplet

1. DigitalOcean → **Create → Droplets**: Ubuntu **24.04**, region **Singapore**,
   at least **1 GB RAM**, add your SSH key. Note the Droplet's IP address.
2. Namecheap → Domain List → **Manage** → **Advanced DNS** (Nameservers: Namecheap BasicDNS):
   * `A Record` — host `@` — value `<Droplet IP>`
   * `A Record` — host `www` — value `<Droplet IP>`
   (delete the default "parking page" records)
3. Log in to the Droplet and run the setup script:
   ```
   ssh root@<Droplet IP>
   git clone https://github.com/<you>/<repo>.git /tmp/tunga
   bash /tmp/tunga/deploy/setup_droplet.sh
   ```
   It asks for the domain, GitHub address and your e-mail, then installs
   PostgreSQL, the website, nginx, HTTPS (Let's Encrypt), the firewall and a
   daily backup. It writes the settings to `/srv/tunga/app/.env`, with new
   secret keys, and prints the **Django admin address** — write it down.
   (Private repository: use a GitHub "deploy key" or a personal access token in the address.)
4. Create the first Django superuser:
   ```
   cd /srv/tunga/app && sudo -u tunga /srv/tunga/venv/bin/python manage.py createsuperuser
   ```
5. Fill the missing values in `/srv/tunga/app/.env` (reCAPTCHA keys, Cloudinary
   if you want it) with `nano /srv/tunga/app/.env`, then run the update script.

**Update the site after a `git push`:**
```
bash /srv/tunga/app/deploy/update.sh
```

Useful commands: `systemctl status tunga` · `journalctl -u tunga -n 100` (errors) ·
`systemctl restart tunga` · `certbot renew --dry-run`.

---

## After the site is live (both ways)

1. **Google sign-in** — Google Cloud Console → APIs & Services → Credentials →
   your OAuth client:
   * Authorized JavaScript origins: `https://yourdomain.com`, `https://www.yourdomain.com`
   * Authorized redirect URIs: `https://yourdomain.com/accounts/google/login/callback/`
     (and the same with `www.`)
   Then in the Django admin → Social applications → Google: make sure the
   site (your domain) is selected.
2. **reCAPTCHA** — https://www.google.com/recaptcha/admin → your key → add
   `yourdomain.com` to the domains.
3. **Emails** — Super Admin → System Settings: send a test email.
4. **Restore** your backup from Render (Super Admin → Backup & Restore).
5. Remove the testing notice when going live (`templates/portal/_testing_notice.html`
   and its line in `templates/base.html`).

## Problems

| You see | Fix |
|---|---|
| `Bad Request (400)` | The address is not allowed: set `SITE_DOMAIN` (and/or `ALLOWED_HOSTS`) |
| `CSRF verification failed` on login / forms | Same as above, then redeploy / restart |
| Page without styles | `python manage.py collectstatic --noinput` (deploy does it) |
| `Server Error (500)` | Read the log: App Platform → Runtime Logs; Droplet → `journalctl -u tunga -n 100` |
| Deploy stops with "Set the SECRET_KEY…" | Add `SECRET_KEY` to the environment variables |
| Photos disappear after a deploy (App Platform) | Use `MEDIA_STORAGE=cloudinary` or `spaces` |
| Can't log in on `http://` | Normal: login only works on `https://` |

Health check address (for DigitalOcean / uptime monitors): `https://yourdomain.com/healthz/`
