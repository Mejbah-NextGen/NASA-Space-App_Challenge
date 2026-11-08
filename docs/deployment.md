# Deployment

## Required production services

- Python 3.12 runtime
- PostgreSQL
- HTTPS-capable reverse proxy/load balancer
- persistent/private media storage appropriate to the hosting platform
- production email delivery
- optional weather egress to Open-Meteo
- optional server-side AI provider

## Production environment

Use `config.settings.production` and configure at least:

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=generate-a-unique-random-secret-with-at-least-50-characters
ALLOWED_HOSTS=farm.example.com
CSRF_TRUSTED_ORIGINS=https://farm.example.com
DATABASE_URL=postgresql://user:password@db-host:5432/farm_time_machine
POSTGRES_SSLMODE=require
CACHE_BACKEND=django.core.cache.backends.redis.RedisCache
CACHE_LOCATION=redis://cache-host:6379/1
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
DEMO_MODE=false
SECURE_SSL_REDIRECT=true
TRUST_X_FORWARDED_PROTO=true
TRUST_X_FORWARDED_FOR=true
```

Production settings fail closed unless PostgreSQL, a non-console email backend, and a shared atomic cache are configured. Enable weather or AI only after provider terms, privacy, credentials, monitoring, and failure behavior have been reviewed.

`TRUST_X_FORWARDED_PROTO=true` and `TRUST_X_FORWARDED_FOR=true` are safe only when the application is reachable exclusively through a trusted reverse proxy or load balancer. The proxy must remove client-supplied forwarded headers and set `X-Forwarded-Proto` to the actual request scheme and `X-Forwarded-For` to the canonical client address. Leave both flags `false` for direct deployments or when that boundary is not guaranteed. Login throttling uses `REMOTE_ADDR` unless `TRUST_X_FORWARDED_FOR` is explicitly enabled.

## Build/release commands

```bash
python -m pip install -r requirements.txt
python manage.py check
python manage.py test
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check --deploy
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60
```

Do not run `seed_demo` as part of a release. The command rejects production settings, but deployment automation should not call it at all.

## Security checklist

- Rotate any credential ever exposed in the original static prototype; do not copy it into this project.
- Generate a unique Django secret and provider keys.
- Restrict `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
- Confirm forwarded protocol/client-address headers are overwritten by a trusted proxy before enabling `TRUST_X_FORWARDED_PROTO` or `TRUST_X_FORWARDED_FOR`; never trust a header supplied directly by the client.
- Keep secure cookies, HTTPS redirect, HSTS, content sniffing protection, and frame denial enabled.
- Restrict database security groups and use TLS.
- Store private uploads outside a public bucket. The application serves consultation media through participant/admin-authorized endpoints and profile images through a self-only endpoint; preserve those boundaries when using object storage.
- Configure upload scanning if real professional documents or crop images are accepted.
- Configure login/AI rate-limit storage in a shared cache for multi-worker deployments. The local-memory cache is development-only.
- Never log passwords, reset/verification tokens, Authorization headers, API keys, or consultation contents.
- Keep Admin accounts minimal and protect them with the organization’s operational controls.

## Data operations

- Treat source attribution, geographic resolution, units, and coverage as required metadata.
- Import unverified/demo data as sample or under-review, never verified.
- Back up PostgreSQL and media independently; test restoration.
- Define retention for AI conversations, consultation attachments, support tickets, and audit events.
- Monitor failed CSV jobs, stale weather data, provider latency, HTTP 4xx/5xx rates, and verification/admin actions.

## Static and media

WhiteNoise serves versioned static assets through Django/Gunicorn for a straightforward deployment. User-uploaded media is different: use private object storage or an authorized download endpoint for production. The development `MEDIA_URL` helper is enabled only with debug settings.

## Deployment checks

Run from a clean release using production settings:

```bash
python manage.py makemigrations --check
python manage.py migrate --plan
python manage.py check --deploy
python manage.py test
```

Smoke-test:

- `/`, `/weather/`, `/history/`, `/data-sources/`
- login/reset and secure POST logout
- each role dashboard and cross-role denial
- Farmer ownership/privacy paths
- assigned versus unassigned Agriculturalist cases
- optional Agriculturalist credential review and data-import failure handling
- AI configured and fallback modes
- 375, 390, 768, 1024, and 1440 px layouts

## Remaining production integrations

The code supplies integration boundaries, but a real deployment must choose/configure:

- authoritative historical agriculture/NASA-derived datasets and calibration methodology;
- an approved Bangladesh district/upazila coordinate registry;
- production email provider;
- private media storage and malware scanning;
- shared cache/rate-limit backend;
- optional AI provider and privacy terms;
- monitoring, alerting, backup, incident response, and data-retention policies.
