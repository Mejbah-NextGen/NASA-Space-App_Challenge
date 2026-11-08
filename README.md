* [ ]

# Farm Time Machine

Farm Time Machine is a public-first, role-based agricultural decision-support platform built with Django. Visitors can explore clearly sourced weather, historical agriculture, and the crop-health reference library without an account. Farmers can manage farms, compare deterministic scenarios, record decisions, and collaborate with Agriculturalists. Agriculturalists work only with assigned and consented cases. Platform Admins manage accounts, optional credential-review badges, content, data provenance, and audit records.

The application is designed for Bangladesh-focused demonstration workflows. It distinguishes live, verified, unavailable, and demonstration data throughout the interface. It does not claim to predict yields or replace qualified local agricultural advice.

## Main capabilities

- Public home, current weather, seven-day forecast, agricultural history, crop insights, searchable crop-disease guidance, NASA agriculture news links, methodology, data sources, and learning content.
- Email-based custom user model with Farmer, Agriculturalist, and Admin roles.
- Farmer farm/field/crop/activity/task management with ownership protection.
- Transparent rule-based Farm Simulator with saved scenarios and comparisons.
- Searchable decision timeline with recorded real outcomes.
- Open Agriculturalist directory with credential-review badges, assigned consultations, threaded replies, recommendations, and revocable farm-data consent.
- Agriculturalist case dashboard, assigned farmers, recommendations, questions, and learning-author workflow.
- Custom platform Admin dashboard for users, optional Agriculturalist credential review, datasets, CSV validation, farms, reports, content, weather, settings status, support, and audit logs.
- Server-side weather integration with timeout, cache, provider attribution, and explicit fallback states.
- Server-side AI provider integration with request limits, conversation history, and an honest built-in fallback when no provider is configured.
- Database-backed notifications and support tickets.
- English/Bangla preference support, keyboard-friendly controls, responsive tables/forms, and PDF-aligned desktop/tablet/mobile navigation.

## Technology

- Python 3.12+
- Django 5.2 LTS
- Django Templates, Bootstrap 5, custom CSS, vanilla JavaScript
- Chart.js and Lucide icons
- SQLite in development; PostgreSQL via `DATABASE_URL` in production
- Pillow, Requests, python-dotenv, WhiteNoise, Gunicorn, psycopg

## Project structure

```text
config/                       Split Django settings, root URLs, ASGI/WSGI
apps/accounts/                Custom user, profiles, verification, preferences
apps/core/                    Public pages, support, platform settings, demo seed
apps/farms/                   Farms, fields, crops, activities, tasks
apps/agricultural_data/       Sources, datasets, imports, historical observations
apps/weather/                 Weather storage and Open-Meteo service abstraction
apps/simulations/             Deterministic scenario model and service
apps/decisions/               Farming decisions and observed outcomes
apps/consultations/           Expert assignments, messages, advice, consent
apps/learning/                Draft/review/published learning content
apps/notifications/           Database-backed notifications
apps/ai_assistant/            Server-side chat service and conversation history
apps/dashboard/               Farmer and Agriculturalist dashboards
apps/administration/          Custom Admin workspace and audit log
templates/                    Public, account, farmer, expert, and admin UI
static/                       Shared CSS and JavaScript
fixtures/                     Clearly labeled example CSV data
docs/                         Architecture, data, permissions, UI, deployment
```

## Local setup - Windows PowerShell

From the project root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

If PowerShell blocks virtual-environment activation, use a process-scoped policy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

## Local setup - macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

## Local demo accounts

The following accounts are created only by the guarded `seed_demo` command:

| Role            | Email                              | Password           |
| --------------- | ---------------------------------- | ------------------ |
| Admin           | `admin@farmtime.test`            | `FarmDemo@2026!` |
| Admin           | `operations.admin@farmtime.test` | `FarmDemo@2026!` |
| Agriculturalist | `agriculturalist@farmtime.test`  | `FarmDemo@2026!` |
| Agriculturalist | `soil.expert@farmtime.test`      | `FarmDemo@2026!` |
| Farmer          | `farmer@farmtime.test`           | `FarmDemo@2026!` |
| Farmer          | `salma.farmer@farmtime.test`     | `FarmDemo@2026!` |

`seed_demo` refuses to run unless the explicit development settings module is active with `DEBUG=True` and `DEMO_MODE=True`. It is idempotent, imports the bundled crop-disease reference library when needed, and never runs during deployment. The password above is public development data; never reuse it for a real account.

See [DEMO_ACCOUNTS.md](DEMO_ACCOUNTS.md) for the quick credential table and [README_DEMO.md](README_DEMO.md) for the role-by-role walkthroughs.

Environment configuration

Copy `.env.example` to `.env`. Important variables:

| Variable                       | Purpose                                                                               |
| ------------------------------ | ------------------------------------------------------------------------------------- |
| `DJANGO_SETTINGS_MODULE`     | `config.settings.development` locally; `config.settings.production` in deployment |
| `DJANGO_SECRET_KEY`          | Required long random production secret                                                |
| `DJANGO_DEBUG`               | Development-only debug switch                                                         |
| `DATABASE_URL`               | PostgreSQL connection URL; empty uses local SQLite                                    |
| `CACHE_BACKEND`              | Shared atomic cache backend required in production                                    |
| `CACHE_LOCATION`             | Cache/Redis connection location                                                       |
| `EMAIL_BACKEND`              | Real delivery backend required in production                                          |
| `EMAIL_VERIFICATION_ENABLED` | Temporarily `false`; set `true` to restore signed-link verification enforcement   |
| `DEMO_MODE`                  | Allows clearly labeled demonstration fallbacks and demo seeding                       |
| `WEATHER_LIVE_ENABLED`       | Enables backend Open-Meteo calls                                                      |
| `WEATHER_API_BASE_URL`       | Fixed weather provider endpoint                                                       |
| `AI_API_KEY`                 | Optional server-side provider credential                                              |
| `AI_API_BASE_URL`            | Optional OpenAI-compatible base URL                                                   |
| `AI_MODEL`                   | Provider model identifier                                                             |
| `ALLOWED_HOSTS`              | Production host allowlist                                                             |
| `CSRF_TRUSTED_ORIGINS`       | HTTPS origins allowed for CSRF                                                        |

Never commit `.env`, API credentials, databases, or private uploaded media.

Email verification is currently disabled by default, so new accounts can sign in immediately and no signup verification message is sent. Farmer and Agriculturalist accounts are immediately usable; an Agriculturalist credential review is an optional trust badge, not an access gate. Migration `accounts.0002` preserves existing account state, and the signed-link workflow remains available behind `EMAIL_VERIFICATION_ENABLED=true`.

## Weather integration

The default local configuration uses an explicitly labeled demonstration state so that page rendering never depends on network access. To use live data:

```dotenv
WEATHER_LIVE_ENABLED=true
WEATHER_API_BASE_URL=https://api.open-meteo.com/v1/forecast
```

Requests are made on the server, cached, time-limited, and attributed to Open-Meteo. Provider failures show a clear unavailable state in production or a clearly marked demonstration fallback when `DEMO_MODE=True`. Current measurements are never silently hardcoded as live data.

## AI Farm Assistant

Without an AI configuration, the assistant remains functional through a curated agricultural-help library and labels every response as built-in guidance. To configure an OpenAI-compatible server-side provider:

```dotenv
AI_API_KEY=replace-me
AI_API_BASE_URL=https://provider.example/v1
AI_MODEL=provider-model-name
AI_RATE_LIMIT_PER_MINUTE=10
```

Credentials are read only by Django and never exposed in templates or browser JavaScript. The service sends a small recent conversation window and broad district context only; it does not transmit private farm records. Advice includes uncertainty and an Ask an Expert escalation path.

## Historical CSV imports

The importer accepts UTF-8 CSV files up to 5 MB and 5,000 data rows. It validates all rows before storing observations and records failed jobs without partially importing data.

Historical weather required columns:

```text
district,date
```

Historical crop required columns:

```text
district,crop_name,year
```

Example management command:

```powershell
python manage.py import_agricultural_data fixtures\demo_historical_weather.csv `
  --kind weather `
  --source "Local demonstration pack" `
  --title "Kurigram example history"
```

Do not pass `--verified` for demonstration or unverified data. Platform Admins can also upload a CSV to an existing dataset from **Agricultural Data**.

## Crop-disease reference import

The bundled contributor dataset uses these columns:

```text
Crop,Disease,Information Type,Information
```

It is imported automatically by `seed_demo` when absent, or directly with:

```powershell
python manage.py import_crop_diseases fixtures\crop_disease_treatment.csv
```

The importer validates the file atomically, removes exact duplicates, preserves original information labels, and groups them into seven visualization categories. The resulting 3,047 unique records remain labeled sample/unverified because the supplied file has no author, license, source citations, review date, or regulatory jurisdiction. See [crop-disease data documentation](docs/crop-disease-data.md) and [source register](SOURCES.md).

## Tests and verification

Run the standard project checks:

```powershell
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

Run deployment checks with production-like environment values:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings.production"
$env:DJANGO_SECRET_KEY = "check-only-7Jq2Wr9Lp4Nx8Cv6Bk3Ze5Tm1Hs0Df9Yu2Aa8"
$env:ALLOWED_HOSTS = "farm.example.com"
$env:CSRF_TRUSTED_ORIGINS = "https://farm.example.com"
$env:DATABASE_URL = "postgresql://user:password@db-host:5432/farm_time_machine"
$env:EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
$env:CACHE_BACKEND = "django.core.cache.backends.redis.RedisCache"
$env:CACHE_LOCATION = "redis://cache-host:6379/1"
python manage.py check --deploy
```

Clear those process-scoped variables before returning to development or start a new PowerShell session.

## Production outline

1. Provision PostgreSQL and private media storage appropriate to the deployment target.
2. Configure `config.settings.production` and all environment variables.
3. Install pinned dependencies and run `python manage.py migrate`.
4. Run `python manage.py collectstatic --noinput`.
5. Run `python manage.py check --deploy` and the automated tests.
6. Start with Gunicorn, for example `gunicorn config.wsgi:application` on a supported Unix host.
7. Terminate TLS at the platform/load balancer, preserve forwarded-protocol headers, and restrict network/database access.
8. Configure real email delivery, backups, monitoring, and a private uploaded-media strategy.

Do not run `seed_demo` in production. Do not expose the default demo password. See [deployment guidance](docs/deployment.md) for the full checklist.

## Design and safety notes

- AI Assistant is a global top-right action and never appears in a sidebar.
- Desktop workspaces use a fixed sidebar with POST logout at the bottom.
- Farmer navigation becomes three columns on tablets and two columns below 768 px.
- Profile menus provide Profile, Settings, Security, Notifications, and POST logout.
- Backend mixins and object-filtered querysets enforce role and ownership permissions.
- Any active Agriculturalist can use the workspace; only assigned cases and explicitly consented farm context are accessible.
- Rule-based simulation results are illustrations, not scientific forecasts or confidence scores.
- Every public data experience carries source, location, unit, freshness, and sample/verified state where applicable.

Additional documentation:

- [Demo guide](README_DEMO.md)
- [Demo account quick reference](DEMO_ACCOUNTS.md)
- [Source register](SOURCES.md)
- [Crop-disease data](docs/crop-disease-data.md)
- [Architecture](docs/architecture.md)
- [Database](docs/database.md)
- [Roles and permissions](docs/roles-permissions.md)
- [UI implementation](docs/ui-implementation.md)
- [Deployment](docs/deployment.md)
