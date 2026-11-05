# Database design

## Identity

- `accounts.User`: unique email login, role, profile/contact/location, language, verification and account state.
- `FarmerProfile`: farmer-specific experience and area-unit preference.
- `AgriculturalistProfile`: qualifications, specialization, organization, experience, and approval state.
- `AgriculturalistVerification`: review decision, reviewer, notes, and timestamp.
- `UserPreference`: notification choices.

## Farming

- `Farm` belongs to one Farmer and is archived rather than destructively removed.
- `Field` belongs to a Farm and validates same-unit area against the Farm.
- `Crop` is a reusable name/variety catalog.
- `CropPlanting` links Field and Crop with planting/harvest dates, status, and optional observed yield.
- `FarmActivity` links optional Field/Planting context and validates that all objects belong to the same Farm.
- `FarmTask` tracks due date, status, priority, and optional Field.

Owner plus name and Farm plus Field-name constraints prevent common duplicates. Owner/status/date indexes support dashboard queries.

## Data provenance and weather

- `Region`: unique district/upazila coordinate record.
- `DataSource`: provider, kind, attribution, coverage, cadence, limitations, live/demo state, and freshness.
- `AgriculturalDataset`: source, status, coverage, date range, units, quality notes, and metadata.
- `DataImportJob`: actor, type, filename, validation/import counts, errors, and lifecycle timestamps.
- `HistoricalWeatherObservation`: dated values plus quality flag.
- `HistoricalCropObservation`: crop/year/season production values.
- `WeatherObservation`, `WeatherForecast`, `WeatherAlert`: operational records linked to Region and DataSource.

Unique constraints stop duplicate observations for the same dataset/region/date or source/issued window.

## Simulation and decisions

- `SimulationScenario`: owner, Farm/Field/Crop, planting date, weather assumptions, irrigation, year, and season.
- `SimulationResult`: one-to-one result with stress/suitability, model version, input snapshot, explanation, and disclaimer.
- `FarmingDecision`: owner-scoped decision with optional Field, Planting, and Simulation links.
- `DecisionOutcome`: one-to-one real observation after the decision date.

Computed simulation values are stored because they represent a versioned run whose input snapshot must remain reviewable.

## Consultations

- `Consultation`: Farmer request, optional assigned Agriculturalist and Farm, priority, status, and close timestamp.
- `ExpertAssignment`: one active case assignment with actor and lifecycle dates.
- `ConsultationMessage`: participant-only chronological thread.
- `ExpertRecommendation`: assigned-expert draft/published advice and priority.
- `FarmDataConsent`: one consultation-specific Farm share, scope, grant, and revocation time.

Model validation ensures role, ownership, assignment, and consent relationships agree. Views add request-user authorization.

## Content and platform

- `LearningCategory`, `LearningArticle`: authored content with language and editorial status.
- `Notification`: user-scoped kind, body, destination, and read timestamp.
- `SupportTicket`: requester, priority, state, and staff response.
- `PlatformSetting`: deliberately limited JSON settings; secrets do not belong here.
- `AuditLog`: actor, safe action/target metadata, result, IP, and timestamp.
- `AIConversation`, `AIMessage`: owner-scoped chat history with source/fallback label.

## Migrations

Every local model app has a checked-in `0001_initial.py` migration. Verify drift with:

```powershell
python manage.py makemigrations --check
```

Create schema in a new environment with:

```powershell
python manage.py migrate
```

SQLite is intended for local development. Production uses PostgreSQL through `DATABASE_URL`.
