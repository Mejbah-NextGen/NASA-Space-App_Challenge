# Crop disease reference dataset

## Purpose and status

The crop-health library uses the contributor-supplied `fixtures/crop_disease_treatment.csv` file. It provides narrative material for browsing symptoms, disease biology, field practices, monitoring, and treatment references.

This file is **sample, unverified contributor data**. It is not a NASA dataset and must not be described as NASA-reviewed agronomy. The supplied file does not identify its original author, citations, license, review date, geographic scope, or regulatory jurisdiction.

The application therefore stores it as an `AgriculturalDataset` with `SAMPLE` status and a demonstration `DataSource`. Public pages repeat that limitation. Chemical names, application rates, intervals, protective equipment, resistance-management instructions, and pre-harvest intervals must be checked against current local regulations and product labels with a qualified agriculturalist.

## Supplied file profile

| Measure | Value |
|---|---:|
| Input rows | 3,110 |
| Unique guidance rows | 3,047 |
| Exact duplicate rows skipped | 63 |
| Crops | 42 |
| Crop-disease pairs | 858 |
| Distinct disease names | 644 |
| Raw information-type labels | 723 |
| Blank required values | 0 |
| SHA-256 | `9B12C2CCC7F5FF87FF9681B963383A3B4F07174275DAF1FEF432FCA1CF41CCF2` |

The checksum identifies the file supplied on November 8, 2026. A different checksum means the input changed and should be reviewed before its metadata is updated.

## CSV contract

The importer accepts a UTF-8 CSV no larger than 5 MB and 5,000 data rows. These columns are required:

```text
Crop,Disease,Information Type,Information
```

All four values are required on each non-empty row. The importer validates field lengths and rejects the whole file before writing anything when validation fails.

## Importing

From the project root, after migrations:

```powershell
python manage.py import_crop_diseases fixtures\crop_disease_treatment.csv
```

The command is atomic and idempotent. It:

1. validates and hashes the complete file;
2. removes repeated input rows using normalized crop, disease, and information-type keys plus exact guidance content;
3. creates or updates the explicitly unverified source and sample dataset;
4. creates unique crop-disease pairs;
5. stores each unique guidance entry with its original row number, raw information type, normalized category, and content hash;
6. records a completed `DataImportJob`; and
7. prints received, unique, skipped, created, and total counts.

Running the same command again does not duplicate diseases or guidance. The second run creates another import audit record and reports zero newly created library records.

## Storage model

`CropDisease` represents a crop/disease pair within one provenance-labelled `AgriculturalDataset`.

`DiseaseGuidance` stores:

- the related crop/disease pair;
- the original `Information Type` value;
- one normalized display category;
- the original narrative text;
- a SHA-256 content hash; and
- the first source CSV row where the entry appeared.

The original label and text are never replaced by the normalized category. This keeps the import auditable while allowing readable filters and charts.

## Category normalization

The source contains 723 information-type labels, including spelling variants and very specific one-off labels. The importer applies an ordered, deterministic keyword mapping to seven display categories:

| Category | Examples of matching concepts |
|---|---|
| Identification & symptoms | symptoms, diagnosis, signs, affected parts, damage |
| Biological & organic options | biological control, organic options, microbial control |
| Treatment & application | chemicals, fungicides, sprays, dosage, copper, curative treatment |
| Prevention & field practice | sanitation, rotation, pruning, irrigation, resistant varieties, field management |
| Disease biology & risk | pathogen, disease cycle, spread, survival, infection, environmental conditions |
| Impact & monitoring | yield loss, severity, scouting, thresholds, forecasting |
| Other / context | material not matched by the preceding categories |

Matching order matters. For example, “Biological Control” is categorized as biological guidance before the broader word “control” can place it under field practice. The normalization rules live in `import_crop_diseases.py`; changing them requires a version bump and a reviewed re-import strategy.

## Public experience

The public route is `/crop-health/`. It provides:

- overall crop, crop-disease pair, and guidance-entry counts;
- a top-crops bar chart based on distinct pairs in this file;
- a normalized guidance-category chart;
- free-text search across crop, disease, raw type, and guidance content;
- crop and category filters;
- paginated disease cards; and
- visible source, sample-status, and treatment-safety notices.

Chart counts describe the contents of this reference file. They do **not** represent disease incidence, prevalence, severity, or probability in a farmer's location. Satellite and weather observations may provide environmental context, but they do not confirm a crop diagnosis or validate a chemical recommendation.

## Maintenance checklist

Before importing a replacement file:

1. document its owner, license, citations, geography, and review date;
2. retain the original file checksum;
3. have locally qualified reviewers check treatment and dosage content;
4. confirm that banned or obsolete products are not presented as current advice;
5. run the focused agricultural-data tests; and
6. verify the crop-health page at mobile and desktop widths.
