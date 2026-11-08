# Farm Time Machine sources

Last reviewed: 8 November 2026

This file separates operational data, demonstration data, reference material, and the user-supplied crop-disease dataset. A link here does not mean that Farm Time Machine currently ingests that source or that NASA reviewed or endorsed this application.

## User-provided crop-disease dataset

- Repository copy: `fixtures/crop_disease_treatment.csv`
- Original filename: `crop_disease_treatment (1).csv`
- Columns: `Crop`, `Disease`, `Information Type`, `Information`
- Original rows: 3,110
- Unique imported guidance rows: 3,047
- Crops: 42
- Distinct crop/disease pairs: 858
- SHA-256: `9B12C2CCC7F5FF87FF9681B963383A3B4F07174275DAF1FEF432FCA1CF41CCF2`

The supplied file did not include an author, upstream citations, license, review date, geographic scope, or pesticide-regulatory jurisdiction. The application therefore labels it as user-provided reference/demo material, not NASA data and not verified agronomic advice. Product names, doses, pre-harvest intervals, and legal approvals must be checked against the current local label and a qualified agriculturalist.

Implementation and category-normalization details are documented in [`docs/crop-disease-data.md`](docs/crop-disease-data.md).

## NASA and Space Apps references

- [NASA Space Apps — About](https://www.spaceappschallenge.org/about/) — explains the hackathon and its use of open NASA and partner-agency data.
- [2025 NASA Farm Navigators challenge](https://www.spaceappschallenge.org/2025/challenges/nasa-farm-navigators-using-nasa-data-exploration-in-agriculture/) — agricultural data-exploration challenge and design context.
- [2024 Leveraging Earth Observation Data for Informed Agricultural Decision-Making](https://www.spaceappschallenge.org/nasa-space-apps-2024/challenges/leveraging-earth-observation-data-for-informed-agricultural-decision-making/) — prior Space Apps agriculture challenge.
- [NASA Agriculture portal](https://science.nasa.gov/earth/explore/agriculture/) — overview of NASA missions, applications, and agriculture news.
- [NASA Earth Action Agriculture](https://science.nasa.gov/earth-science/earth-action/agriculture/) — applied Earth-observation work for agriculture and food security.

## NASA data and mission references

- [NASA POWER](https://power.larc.nasa.gov/) and [Agroclimatology methodology](https://power.larc.nasa.gov/docs/methodology/communities/) — global solar and meteorological analysis-ready data and the agricultural community profile.
- [NASA POWER temporal APIs](https://power.larc.nasa.gov/docs/services/api/temporal/) — supported daily, monthly, hourly, and climatology services and output formats.
- [SMAP mission](https://science.nasa.gov/mission/smap/) — global soil-moisture and freeze/thaw observations.
- [Landsat agriculture and food security](https://science.nasa.gov/mission/landsat/benefits/agriculture-food-security/) — agricultural applications of the NASA/USGS Landsat record.
- [Landsat data overview](https://science.nasa.gov/mission/landsat/data-overview/) — Landsat access and product context.
- [NASA Earth science data gateway](https://science.nasa.gov/earth/data/) — entry point for NASA Earth-observation archives.
- [Bangladesh rice crop-mask reference](https://glam1.gsfc.nasa.gov/api/doc/cropmask/v1/GDA-CropID-Bangladesh_2020_Rice) — NASA Harvest/GLAM crop-mask documentation relevant to Bangladesh.

These sources provide context and future integration paths. Unless a page explicitly says otherwise, the current local demo does not download or display measurements from these APIs.

## Curated agriculture news links shown in the application

- [Separating Wheat from Chaff — from Space](https://science.nasa.gov/mission/landsat/separating-wheat-from-chaff-from-space/) — NASA Landsat, 8 September 2026.
- [NASA Scientists Map Plant Productivity with Data from Ocean Satellite](https://science.nasa.gov/blogs/science-news/2025/08/29/nasa-scientists-map-plant-productivity-with-data-from-ocean-satellite/) — NASA Science, 29 August 2025.
- [NASA-ISRO Mission Will Map Farmland From Planting to Harvest](https://www.jpl.nasa.gov/news/nasa-isro-mission-will-map-farmland-from-planting-to-harvest/) — NASA JPL, 12 March 2025.
- [NASA Data Helps Bangladeshi Farmers Save Water, Money, Energy](https://www.nasa.gov/centers-and-facilities/goddard/nasa-data-helps-bangladeshi-farmers-save-water-money-energy/) — Bangladesh irrigation application case study.
- [South Asian Farmers Fine-Tune When to Water with Landsat](https://science.nasa.gov/missions/landsat/south-asian-farmers-fine-tune-when-to-water-with-landsat/) — Landsat irrigation case study.

News cards are curated static links, not a live feed. Their publication dates and destination pages remain visible so visitors can evaluate freshness.

## Other operational and demo sources

- [Open-Meteo forecast API](https://open-meteo.com/en/docs) — optional live weather provider when `WEATHER_LIVE_ENABLED=true`.
- `fixtures/demo_historical_weather.csv` — synthetic, clearly labeled local-development weather history.
- `apps/core/management/commands/seed_demo.py` — creates synthetic farms, weather, crop observations, consultations, and learning records for local demonstrations.

Open-Meteo terms and attribution requirements should be reviewed before production deployment. Built-in weather and farm records are demonstrations and must not be described as observed NASA data.

