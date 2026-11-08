# Architecture

## Overview

Farm Time Machine is a modular Django monolith. Django owns authentication, authorization, HTML rendering, forms, sessions, ORM persistence, file validation, external-provider calls, caching, and asynchronous-feeling browser interactions through small fetch requests. There is no separate JavaScript application or client-side secret.

```text
Browser
  -> Django URLs and middleware
     -> role/object permission mixins
        -> forms and views
           -> domain services
              -> Django ORM / PostgreSQL
              -> weather or optional AI provider (server-side only)
```

## Settings

- `config/settings/base.py` contains shared apps, middleware, templates, database parsing, locale, static/media, cache, and integration settings.
- `config/settings/development.py` enables local debug behavior and SQLite by default.
- `config/settings/production.py` requires an external secret and host allowlist, disables demo mode, and enables secure cookies, HTTPS redirect, HSTS, and manifest static storage.

`manage.py` defaults to development. WSGI/ASGI default to production so a deployment cannot silently start with debug settings.

## Modules

- **accounts**: email-authenticated custom user, profiles, verification, preferences, signup/login/reset/profile/settings.
- **core**: public information pages, support tickets, safe platform settings, demo seed command.
- **farms**: owner-scoped farms, fields, crops, planting records, activities, and tasks.
- **agricultural_data**: source registry, datasets, import jobs, historical weather/crop records, filters, and CSV import service.
- **weather**: weather persistence plus the Open-Meteo service boundary.
- **simulations**: deterministic scenario inputs/results and a versioned baseline service.
- **decisions**: decision journal and real observed outcomes.
- **consultations**: assigned expert cases, messages, recommendations, and consent.
- **learning**: multilingual article draft/review/publish workflow.
- **notifications**: scoped read/unread notification history.
- **ai_assistant**: conversations, provider adapter, fallback library, and rate-limited chat endpoint.
- **dashboard**: query-composed Farmer/Agriculturalist overview pages.
- **administration**: custom Admin workspace, data import, review actions, safe reports, and audit records.

## Service boundaries

Business logic that should be reused or tested independently lives outside views:

- `weather.services.get_weather`
- `agricultural_data.services.import_historical_csv`
- `simulations.services.run_baseline` / `calculate_and_store`
- `consultations.services.assign_consultation` / `notify_message`
- `notifications.services.create_notification`
- `ai_assistant.services.generate_reply`
- `administration.services.record_audit`

## Security boundaries

- The custom user model is present in the initial migration.
- Roles are server-owned model fields and never editable through public profile forms.
- Role mixins deny cross-workspace access with HTTP 403.
- Owner-sensitive views filter their queryset by the signed-in user before object lookup, producing a privacy-preserving 404 for another user’s object.
- Any active Agriculturalist can use the workspace and accept an assigned consultation. Credential review is an informational badge; private Farm details still require matching, active Farmer consent.
- All state changes use POST and CSRF protection.
- Uploads are constrained by size, extension/type, and domain validation.
- Login and AI endpoints use cache-backed request limits.
- External endpoints come from trusted environment configuration, not request parameters.
- Audit metadata filters obvious secret keys and never intentionally records messages, passwords, tokens, or uploaded content.

## Rendering strategy

Two shared shells are used:

- `templates/public/base_public.html`
- `templates/dashboard/base_dashboard.html`

Feature templates inherit those shells. CSS tokens and responsive behavior live in `static/css/app.css`; global progressive enhancement and the AI drawer live in `static/js/app.js`. Chart data is serialized by Django and rendered with Chart.js.

## External dependencies

The system remains useful without external services:

- Disabled/unavailable weather becomes an unavailable state or a clearly labeled local demonstration state.
- Unconfigured/unavailable AI becomes a curated, explicitly labeled help response.
- Console email supports local verification/reset testing; production needs a real email backend.

This graceful degradation is deliberate and never presents fallback values as verified live observations.
