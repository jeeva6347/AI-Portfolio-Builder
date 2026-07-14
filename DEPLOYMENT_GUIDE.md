# Deployment Guide

## Prerequisites

- Python 3.10+
- pip
- Git
- A server (VPS, cloud VM, PaaS like Heroku/Railway)
- (Optional) MySQL database for production
- A domain name (optional, for custom domains)

---

## 1. Clone the Repository

```bash
git clone https://github.com/your-username/aiportfoliobuilder.git
cd aiportfoliobuilder/aiportfoliobuilder
```

---

## 2. Set Up Virtual Environment

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Core Django Settings
DJANGO_SECRET_KEY=your-very-long-random-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (use MySQL in production)
DB_ENGINE=mysql
DB_NAME=aiportfolio_db
DB_USER=db_user
DB_PASSWORD=db_password
DB_HOST=localhost
DB_PORT=3306

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=your-google-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-google-client-secret

# GitHub OAuth
GITHUB_OAUTH_CLIENT_ID=your-github-client-id
GITHUB_OAUTH_CLIENT_SECRET=your-github-client-secret

# Session
SESSION_COOKIE_AGE=1209600

# Security (production)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
```

---

## 5. Database Setup

### SQLite (development only)
```bash
python manage.py migrate
python manage.py createsuperuser
```

### MySQL (production)
1. Create the database:
   ```sql
   CREATE DATABASE aiportfolio_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'db_user'@'localhost' IDENTIFIED BY 'db_password';
   GRANT ALL PRIVILEGES ON aiportfolio_db.* TO 'db_user'@'localhost';
   FLUSH PRIVILEGES;
   ```
2. Run migrations:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

---

## 6. Collect Static Files

```bash
python manage.py collectstatic --no-input
```

---

## 7. Run System Checks

```bash
python manage.py check
python manage.py check --deploy
```

Resolve any warnings before going live.

---

## 8. Configure OAuth Apps

### Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs: `https://yourdomain.com/accounts/social/google/login/callback/`
6. Copy Client ID and Secret to `.env`

### GitHub OAuth
1. Go to [GitHub Developer Settings](https://github.com/settings/applications/new)
2. Set Homepage URL: `https://yourdomain.com`
3. Set Callback URL: `https://yourdomain.com/accounts/social/github/login/callback/`
4. Copy Client ID and Secret to `.env`

### Django Admin: Social Applications
After running the server, go to `/admin/` and add `SocialApp` records for Google and GitHub with your client credentials. Set the site to your domain.

---

## 9. Configure Web Server

### Gunicorn + Nginx (recommended)

Install Gunicorn:
```bash
pip install gunicorn
```

Start Gunicorn:
```bash
gunicorn aiportfoliobuilder.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

Sample Nginx configuration:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    location /static/ {
        alias /path/to/aiportfoliobuilder/staticfiles/;
    }

    location /media/ {
        alias /path/to/aiportfoliobuilder/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL Certificate (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## 10. Systemd Service (Linux)

Create `/etc/systemd/system/aiportfolio.service`:
```ini
[Unit]
Description=AI Portfolio Builder Django
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/aiportfoliobuilder/aiportfoliobuilder
ExecStart=/path/to/venv/bin/gunicorn aiportfoliobuilder.wsgi:application --bind 127.0.0.1:8000 --workers 3
EnvironmentFile=/path/to/.env
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable aiportfolio
sudo systemctl start aiportfolio
```

---

## 11. Run Automated Tests

```bash
python manage.py test
```

All 75 tests should pass.

---

## 12. Post-Deployment Checklist

- [ ] `DJANGO_DEBUG=False` in `.env`
- [ ] Long, random `DJANGO_SECRET_KEY` set
- [ ] Database running and migrated
- [ ] Static files collected
- [ ] Media directory writable
- [ ] SSL certificate installed and valid
- [ ] OAuth apps configured with production callback URLs
- [ ] `python manage.py check --deploy` shows no warnings
- [ ] Superuser account created
- [ ] `ALLOWED_HOSTS` set to production domain
- [ ] Email backend configured for transactional emails
- [ ] Backup strategy in place for media and database

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Yes | insecure default | Long random string for cryptography |
| `DJANGO_DEBUG` | Yes | `True` | Set to `False` in production |
| `DJANGO_ALLOWED_HOSTS` | Yes | `127.0.0.1,localhost` | Comma-separated hostnames |
| `DB_ENGINE` | No | `sqlite` | `sqlite` or `mysql` |
| `DB_NAME` | If MySQL | — | Database name |
| `DB_USER` | If MySQL | — | Database user |
| `DB_PASSWORD` | If MySQL | — | Database password |
| `DB_HOST` | If MySQL | `localhost` | Database host |
| `DB_PORT` | If MySQL | `3306` | Database port |
| `EMAIL_BACKEND` | No | console | Email backend |
| `GOOGLE_OAUTH_CLIENT_ID` | For OAuth | `` | Google OAuth client ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | For OAuth | `` | Google OAuth secret |
| `GITHUB_OAUTH_CLIENT_ID` | For OAuth | `` | GitHub OAuth client ID |
| `GITHUB_OAUTH_CLIENT_SECRET` | For OAuth | `` | GitHub OAuth secret |
