# Farm Time Machine Demo Guide

This guide is for the local demonstration environment. The accounts, password, weather, historical observations, farms, and advice below are synthetic test data. Do not use them in production or for real agricultural decisions.

## Start the demo

### Windows PowerShell

~~~powershell
cd D:\NASA-Space-App_Challenge
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
~~~

### macOS/Linux

~~~bash
source .venv/bin/activate
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
~~~

Open http://127.0.0.1:8000/.

## Demo accounts

Every account uses the development-only password **FarmDemo@2026!**.

| Role | Persona | Email | Main demo scenario |
| --- | --- | --- | --- |
| Admin | System Admin | admin@farmtime.test | Users, expert verification, data, support, and audit |
| Admin | Nadia Islam | operations.admin@farmtime.test | Operations, content review, and Salma's workflow |
| Agriculturalist | Dr. Ayesha Rahman | agriculturalist@farmtime.test | Rahim's irrigation consultation |
| Agriculturalist | Dr. Farhana Akter | soil.expert@farmtime.test | Salma's soil-moisture and tomato consultation |
| Farmer | Rahim Mia | farmer@farmtime.test | Rice farm, irrigation scenario, decision, and consultation |
| Farmer | Salma Begum | salma.farmer@farmtime.test | Tomato farm, drip-irrigation scenario, tasks, and consultation |

Both Agriculturalist accounts carry a demonstration-only credential-review badge. Review is informational; any active Agriculturalist can use the workspace and collaborate on an assigned case. The main admin is a superuser; the operations admin uses the project's custom platform-admin workspace without Django superuser privileges.

## Seeded demonstration data

Running **python manage.py seed_demo** creates or refreshes:

- Two farms with separate owners, fields, crop plantings, activities, and upcoming tasks.
- Saved rice and tomato simulations with calculated rule-based results.
- Farming decisions and recorded outcomes linked to those simulations.
- Two active consultations with assignments, consented farm context, messages, and published recommendations.
- Two Agriculturalist profiles with demonstration credential-review records.
- Two published learning articles.
- Synthetic historical crop and weather observations for charts.
- The bundled contributor crop-disease library: 42 crops, 858 crop/disease pairs, and 3,047 unique guidance records.
- NASA POWER, SMAP, Landsat, and Space Apps reference-source cards (no NASA measurements are imported by the seed command).
- A seven-day demonstration forecast and a clearly labeled weather alert.
- Support tickets, user notifications, and an admin audit event.

All sample weather, historical, professional, and advisory information is explicitly demonstration-only.

## Suggested walkthroughs

### Farmer: Rahim Mia

1. Sign in as farmer@farmtime.test.
2. Open **My Farm** and inspect Rahim Family Farm, North Field, the rice planting, activity, and task.
3. Open **Simulator** and review the saved 2019 rice comparison.
4. Open **Decisions** and inspect the shorter-irrigation decision and outcome.
5. Open **Consultations** to read Dr. Ayesha Rahman's response and recommendation.

### Farmer: Salma Begum

1. Sign in as salma.farmer@farmtime.test.
2. Review Salma Vegetable Farm, the tomato planting, and two upcoming tasks.
3. Compare the saved tomato dry-week simulation with the recorded drip-schedule decision.
4. Open the tomato leaf-curl consultation to see shared farm context and expert guidance.

### Agriculturalist

1. Sign in as either agriculturalist account.
2. Open the assigned-question inbox.
3. Review only the farmer data shared through the consultation consent.
4. Inspect the published recommendation and learning article for that persona.

### Admin

1. Sign in as either admin account.
2. Review users, optional Agriculturalist credential badges, farms, data sources, datasets, and weather alerts.
3. Inspect the two support tickets and the audit log.
4. Use the custom platform-admin tools without changing the synthetic-data labeling.

## Refresh the demo safely

The seed is idempotent: rerunning it refreshes the named demo records without deleting unrelated records or creating duplicate demo workflows.

~~~powershell
python manage.py migrate
python manage.py seed_demo
~~~

To verify the seed:

~~~powershell
python manage.py check
python manage.py test apps.core.test_seed_demo
~~~

## Full local reset

The following deletes every database row in the active database while preserving the schema. Use it only with the disposable local development database:

~~~powershell
python manage.py flush --noinput
python manage.py seed_demo
~~~

Never run **flush** or **seed_demo** against production or a database containing data you need.

## Safety

- The seed command refuses to run unless the development settings, DEBUG=True, and DEMO_MODE=True are active.
- The .test email addresses are not delivery accounts.
- The shared password is public development data. Never reuse it.
- Do not present the seeded weather, historical values, credentials, simulations, or recommendations as verified real-world information.

For installation and architecture details, see [README.md](README.md). For production requirements, see [docs/deployment.md](docs/deployment.md).
