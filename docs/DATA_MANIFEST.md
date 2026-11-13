# Data manifest (generated)

Generated from `data/manifest.csv` by `python -m mal.fetch` - do not edit by hand.
The central data reference and standards are in [DATA.md](../DATA.md).
All inputs are open and aggregate; no patient-level records. Raw files live in
`data/raw/` (gitignored); only the manifest is committed. Licences are as stated
by each provider at access time - check before redistributing any file.

## Sources

| Source | Used for | Files | Rows | Last accessed (UTC) | Licence | Fallback |
|---|---|---|---|---|---|---|
| MAP PfPR survey points | Pf prevalence target (notebook 01) | 4 | 10943 | 2026-11-12T09:35:14Z | CC BY 4.0 (Malaria Atlas Project); per-record permissions_info applies | Manual CSV export from data.malariaatlas.org; DHS/MIS needs registration (last resort) |
| MAP PvPR survey points | P. vivax presence (notebook 02 A) | 4 | 1987 | 2026-11-12T09:35:18Z | CC BY 4.0 (Malaria Atlas Project); per-record permissions_info applies | Literature and MIS reports only |
| MAP Duffy-negativity phenotype frequency (2011) | P. vivax covariate / explanation | 1 | - | 2026-11-12T09:47:03Z | CC BY 4.0 (Malaria Atlas Project); cite Howes et al. 2011 | Cite the published map (Howes et al. 2011) |
| geoBoundaries gbOpen ADM0-ADM2 | District polygons, gazetteer for the agent | 12 | 781 | 2026-11-12T09:35:03Z | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO); Creative Commons Attribution 4.0 (CC BY 4.0); Open Data Commons Open Database License 1.0; Public Domain | GADM (check licence) |
| WorldClim 2.1 bioclim 30 s (bio1 mean temp, bio12 annual rain) | Rainfall, temperature | 4 | - | 2026-11-12T09:37:37Z | WorldClim 2.1 - free for academic/non-commercial use; cite Fick & Hijmans 2017 | CHIRPS annual rainfall |
| WorldClim 2.1 elevation 30 s (SRTM-based) | Elevation | 4 | - | 2026-11-12T09:37:39Z | WorldClim 2.1 - free for academic/non-commercial use; cite Fick & Hijmans 2017 | SRTM via USGS EarthExplorer |
| MODIS MOD13A1 v061 NDVI, annual median (computed) | Vegetation index | 1 | - | 2026-11-12T10:02:02Z | NASA EOSDIS open data (no restrictions); via Microsoft Planetary Computer | Earth Engine export; else ship without NDVI and list the gap in ASSUMPTIONS.md |
| WorldPop 2020 UN-adjusted 1 km (counts + density) | Population density, population at risk | 8 | - | 2026-11-12T09:38:24Z | CC BY 4.0 (WorldPop) | WorldPop 100 m aggregated |
| GHSL SMOD 2020 degree of urbanisation (R2023A, 1 km) | Urban/rural class | 1 | - | 2026-11-12T09:46:44Z | CC BY 4.0 (European Commission JRC, GHSL R2023A) | WorldPop density >= 300/km2 rule, documented |
| HydroRIVERS v1.0 Africa | Distance to water | 1 | - | 2026-11-12T09:46:55Z | HydroSHEDS licence (free, attribution required) | Natural Earth 10 m rivers |
| Natural Earth 10 m lakes / rivers | Distance to water (lakes) | 2 | - | 2026-11-12T09:46:58Z | Public domain (Natural Earth) | - |
| WHO Malaria Threats Map (xMart public API) | TES efficacy + molecular markers (notebook 02 B/C) | 4 | 6994 | 2026-11-12T09:51:09Z | CC BY-NC-SA 3.0 IGO (WHO Malaria Threats Map) | Manual Excel download from the Threats Map site; WWARN only if approved in time |
| MalariaGEN Pf7 | pfkelch13 / pfmdr1 / pfcrt genotypes by admin-1 x year | 3 | 53270 | 2026-11-12T09:51:12Z | CC BY 4.0 (MalariaGEN Pf7 open release) | Threats Map markers only |
| WHO GHO / World Malaria Report country estimates | Burden cross-check; Pf vs Pv case share | 6 | 394 | 2026-11-12T09:51:21Z | CC BY-NC-SA 3.0 IGO (WHO GHO) | None needed |
| GBIF Plasmodium occurrences | Species records | 4 | 1765 | 2026-11-12T09:51:50Z | Per record (CC0 / CC BY / CC BY-NC) - see 'license' field | Country-level reports only |
| MIS/DHS microscopy tables (manual entry) | P. malariae / P. ovale shares | 1 | - | 2026-11-12T10:22:26Z | Per report (DHS Program / national statistics office) | Country-level reports only |
| WHO guidance PDFs (IRIS) | Agent guideline_search | 3 | - | 2026-11-12T09:52:14Z | CC BY-NC-SA 3.0 IGO (WHO) | National guidelines (e.g. Kenya MoH) |

## Manual steps

- `data/raw/species/mis_microscopy_manual.csv` is typed in by hand from MIS/DHS final report microscopy tables. Record the report title, URL and page per row.
- If any automated source fails at the venue, the manual export used instead must be logged here with the date and the person who downloaded it.

## File manifest

| source_id | rows | accessed_utc | sha256 (first 12) | url |
|---|---|---|---|---|
| gbif_plasmodium_eth | 213 | 2026-11-12T09:51:50Z | `4f4655176739` | https://api.gbif.org/v1/occurrence/search?taxonKey=8364053&country=ET |
| gbif_plasmodium_ken | 662 | 2026-11-12T09:51:33Z | `3384bc99fae9` | https://api.gbif.org/v1/occurrence/search?taxonKey=8364053&country=KE |
| gbif_plasmodium_tza | 167 | 2026-11-12T09:51:45Z | `06158ab902c9` | https://api.gbif.org/v1/occurrence/search?taxonKey=8364053&country=TZ |
| gbif_plasmodium_uga | 723 | 2026-11-12T09:51:40Z | `d8e6048f9760` | https://api.gbif.org/v1/occurrence/search?taxonKey=8364053&country=UG |
| geoboundaries_eth_adm0 | 1 | 2026-11-12T09:34:59Z | `380b89914003` | https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/ETH/ADM0/geoBoundaries-ETH-ADM0.geojson |
| geoboundaries_eth_adm1 | 11 | 2026-11-12T09:35:01Z | `acb690b4f1c3` | https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/ETH/ADM1/geoBoundaries-ETH-ADM1.geojson |
| geoboundaries_eth_adm2 | 74 | 2026-11-12T09:35:03Z | `152af49839e5` | https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/ETH/ADM2/geoBoundaries-ETH-ADM2.geojson |
| geoboundaries_ken_adm0 | 1 | 2026-11-12T09:34:10Z | `89248c71d10e` | https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/KEN/ADM0/geoBoundaries-KEN-ADM0.geojson |
| geoboundaries_ken_adm1 | 47 | 2026-11-12T09:34:18Z | `a3e073594494` | https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/KEN/ADM1/geoBoundaries-KEN-ADM1.geojson |
| geoboundaries_ken_adm2 | 290 | 2026-11-12T09:34:26Z | `af9fd77ad3df` | https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/KEN/ADM2/geoBoundaries-KEN-ADM2.geojson |
| geoboundaries_tza_adm0 | 1 | 2026-11-12T09:34:41Z | `41ab6299edd6` | https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/TZA/ADM0/geoBoundaries-TZA-ADM0.geojson |
| geoboundaries_tza_adm1 | 30 | 2026-11-12T09:34:47Z | `02ffe153dc28` | https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/TZA/ADM1/geoBoundaries-TZA-ADM1.geojson |
| geoboundaries_tza_adm2 | 170 | 2026-11-12T09:34:55Z | `1eb3cbe313f1` | https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/TZA/ADM2/geoBoundaries-TZA-ADM2.geojson |
| geoboundaries_uga_adm0 | 1 | 2026-11-12T09:34:31Z | `5a4c6c87ff2d` | https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/UGA/ADM0/geoBoundaries-UGA-ADM0.geojson |
| geoboundaries_uga_adm1 | 4 | 2026-11-12T09:34:33Z | `44e303862627` | https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/UGA/ADM1/geoBoundaries-UGA-ADM1.geojson |
| geoboundaries_uga_adm2 | 151 | 2026-11-12T09:34:35Z | `1f6954fbd49e` | https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/UGA/ADM2/geoBoundaries-UGA-ADM2.geojson |
| gho_malaria_conf_cases | 40 | 2026-11-12T09:51:21Z | `86da37a94d63` | https://ghoapi.azureedge.net/api/MALARIA_CONF_CASES?$filter=SpatialDim eq 'KEN' or SpatialDim eq 'UGA' or SpatialDim eq 'TZA' or SpatialDim eq 'ETH' |
| gho_malaria_est_cases | 100 | 2026-11-12T09:51:14Z | `4f44ecb1259c` | https://ghoapi.azureedge.net/api/MALARIA_EST_CASES?$filter=SpatialDim eq 'KEN' or SpatialDim eq 'UGA' or SpatialDim eq 'TZA' or SpatialDim eq 'ETH' |
| gho_malaria_est_deaths | 100 | 2026-11-12T09:51:14Z | `99679aa0528e` | https://ghoapi.azureedge.net/api/MALARIA_EST_DEATHS?$filter=SpatialDim eq 'KEN' or SpatialDim eq 'UGA' or SpatialDim eq 'TZA' or SpatialDim eq 'ETH' |
| gho_malaria_est_incidence | 100 | 2026-11-12T09:51:15Z | `5fc2e1602dbe` | https://ghoapi.azureedge.net/api/MALARIA_EST_INCIDENCE?$filter=SpatialDim eq 'KEN' or SpatialDim eq 'UGA' or SpatialDim eq 'TZA' or SpatialDim eq 'ETH' |
| gho_malaria_pf_indig | 40 | 2026-11-12T09:51:15Z | `669ccdb9f99f` | https://ghoapi.azureedge.net/api/MALARIA_PF_INDIG?$filter=SpatialDim eq 'KEN' or SpatialDim eq 'UGA' or SpatialDim eq 'TZA' or SpatialDim eq 'ETH' |
| gho_malaria_pv_indig | 14 | 2026-11-12T09:51:21Z | `c35d2cae1452` | https://ghoapi.azureedge.net/api/MALARIA_PV_INDIG?$filter=SpatialDim eq 'KEN' or SpatialDim eq 'UGA' or SpatialDim eq 'TZA' or SpatialDim eq 'ETH' |
| ghsl_smod_2020 | - | 2026-11-12T09:46:44Z | `a02f4741f4ff` | https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_SMOD_GLOBE_R2023A/GHS_SMOD_E2020_GLOBE_R2023A_54009_1000/V2-0/GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V2_0.zip |
| hydrorivers_af | - | 2026-11-12T09:46:55Z | `63cc615134d8` | https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_af_shp.zip |
| map_duffy_negativity | - | 2026-11-12T09:47:03Z | `ab449aaf1c29` | https://data.malariaatlas.org/geoserver/ows?service=WCS&version=2.0.1&request=GetCoverage&coverageId=Explorer__2011_Duffy_Negativity_Phenotype_Frequency_5k_Decompressed&format=image%2Fgeotiff&subset=Long%2828.8%2C48.2%29&subset=Lat%28-12.0%2C15.1%29 |
| map_pfpr_eth | 1413 | 2026-11-12T09:35:14Z | `6f5aa5efee2b` | https://data.malariaatlas.org/geoserver/Malaria/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=Malaria:202406_Global_Pf_Parasite_Rate_Surveys&outputFormat=application/json&CQL_FILTER=country_id='ETH' |
| map_pfpr_ken | 3607 | 2026-11-12T09:35:08Z | `ece2fc875e4c` | https://data.malariaatlas.org/geoserver/Malaria/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=Malaria:202406_Global_Pf_Parasite_Rate_Surveys&outputFormat=application/json&CQL_FILTER=country_id='KEN' |
| map_pfpr_tza | 4449 | 2026-11-12T09:35:13Z | `727b547bdee5` | https://data.malariaatlas.org/geoserver/Malaria/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=Malaria:202406_Global_Pf_Parasite_Rate_Surveys&outputFormat=application/json&CQL_FILTER=country_id='TZA' |
| map_pfpr_uga | 1474 | 2026-11-12T09:35:09Z | `e8c5dc311b5f` | https://data.malariaatlas.org/geoserver/Malaria/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=Malaria:202406_Global_Pf_Parasite_Rate_Surveys&outputFormat=application/json&CQL_FILTER=country_id='UGA' |
| map_pvpr_eth | 1381 | 2026-11-12T09:35:18Z | `6781a3617629` | https://data.malariaatlas.org/geoserver/Malaria/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=Malaria:202406_Global_Pv_Parasite_Rate_Surveys&outputFormat=application/json&CQL_FILTER=country_id='ETH' |
| map_pvpr_ken | 319 | 2026-11-12T09:35:15Z | `bf120e93b2a3` | https://data.malariaatlas.org/geoserver/Malaria/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=Malaria:202406_Global_Pv_Parasite_Rate_Surveys&outputFormat=application/json&CQL_FILTER=country_id='KEN' |
| map_pvpr_tza | 110 | 2026-11-12T09:35:17Z | `31223c03dcf0` | https://data.malariaatlas.org/geoserver/Malaria/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=Malaria:202406_Global_Pv_Parasite_Rate_Surveys&outputFormat=application/json&CQL_FILTER=country_id='TZA' |
| map_pvpr_uga | 177 | 2026-11-12T09:35:16Z | `47539802da72` | https://data.malariaatlas.org/geoserver/Malaria/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=Malaria:202406_Global_Pv_Parasite_Rate_Surveys&outputFormat=application/json&CQL_FILTER=country_id='UGA' |
| mis_microscopy_manual | 0 | 2026-11-12T10:22:26Z | `244218c6e89f` | manual entry from national MIS/DHS final reports |
| modis_ndvi_2020 | - | 2026-11-12T10:02:02Z | `b42bb6365851` | https://planetarycomputer.microsoft.com/api/stac/v1/collections/modis-13A1-061 (bbox=[28.8, -12.0, 48.2, 15.1], 2020, Terra, median) |
| naturalearth_lakes_10m | - | 2026-11-12T09:46:58Z | `0803a06f9c3c` | https://naciscdn.org/naturalearth/10m/physical/ne_10m_lakes.zip |
| naturalearth_rivers_10m | - | 2026-11-12T09:46:58Z | `ded71b018708` | https://naciscdn.org/naturalearth/10m/physical/ne_10m_rivers_lake_centerlines.zip |
| pf7_marker_genotypes | 16203 | 2026-11-12T09:51:12Z | `9b70d318678a` | https://www.malariagen.net/wp-content/uploads/2023/11/Pf7_drug_resistance_marker_genotypes.txt |
| pf7_resistance_status | 16203 | 2026-11-12T09:51:12Z | `d21b1788fffd` | https://www.malariagen.net/wp-content/uploads/2023/11/Pf7_inferred_resistance_status_classification.txt |
| pf7_samples | 20864 | 2026-11-12T09:51:11Z | `826c188c7d81` | https://www.malariagen.net/wp-content/uploads/2023/11/Pf7_samples.txt |
| who_drug_efficacy_report_2020 | - | 2026-11-12T09:52:03Z | `df6b4063a0d5` | https://iris.who.int/server/api/core/bitstreams/72f1791d-c205-4a26-94a5-6458c4f28eb5/content |
| who_guidelines_malaria_2025 | - | 2026-11-12T09:52:00Z | `41c1cb923973` | https://iris.who.int/server/api/core/bitstreams/26a6af2d-060c-4449-8207-1f25e63c6cc3/content |
| who_mtm_markers_genotypes | 5573 | 2026-11-12T09:51:06Z | `7b3bb3c07c62` | https://xmart-api-public.who.int/MAL_THREATS/FACT_AMDER_GENO_VIEW?$select=CODE,K13_CODE,PROPORTION,GENOTYPE |
| who_mtm_markers_sites | 351 | 2026-11-12T09:50:49Z | `496dda94cc30` | https://xmart-api-public.who.int/MAL_THREATS/FACT_AMDER_MM_VIEW?$filter=ISO2 eq 'KE' or ISO2 eq 'UG' or ISO2 eq 'TZ' or ISO2 eq 'ET' |
| who_mtm_translations | 567 | 2026-11-12T09:51:09Z | `2d1d4f06db8e` | https://xmart-api-public.who.int/MAL_THREATS/TRANSLATIONS?$select=FIELD,VALUE_,EN,DATASET |
| who_mtm_treatment | 503 | 2026-11-12T09:50:43Z | `07c89b7c8643` | https://xmart-api-public.who.int/MAL_THREATS/FACT_TREATMENT_VIEW?$filter=ISO2 eq 'KE' or ISO2 eq 'UG' or ISO2 eq 'TZ' or ISO2 eq 'ET' |
| who_strategy_drug_resistance_africa_2022 | - | 2026-11-12T09:52:14Z | `77cc66aa0f35` | https://iris.who.int/server/api/core/bitstreams/d119a69e-e56d-4c78-a2b9-52572e14217c/content |
| worldclim_bio_eth | - | 2026-11-12T09:37:37Z | `a88ea4a67e45` | https://geodata.ucdavis.edu/climate/worldclim/2_1/tiles/iso/ETH_wc2.1_30s_bio.tif |
| worldclim_bio_ken | - | 2026-11-12T09:35:48Z | `6e939bb35c21` | https://geodata.ucdavis.edu/climate/worldclim/2_1/tiles/iso/KEN_wc2.1_30s_bio.tif |
| worldclim_bio_tza | - | 2026-11-12T09:36:47Z | `5c15ff1df802` | https://geodata.ucdavis.edu/climate/worldclim/2_1/tiles/iso/TZA_wc2.1_30s_bio.tif |
| worldclim_bio_uga | - | 2026-11-12T09:36:03Z | `c8d1452c7f1e` | https://geodata.ucdavis.edu/climate/worldclim/2_1/tiles/iso/UGA_wc2.1_30s_bio.tif |
| worldclim_elev_eth | - | 2026-11-12T09:37:39Z | `b65d2261fcd3` | https://geodata.ucdavis.edu/climate/worldclim/2_1/tiles/iso/ETH_wc2.1_30s_elev.tif |
| worldclim_elev_ken | - | 2026-11-12T09:35:49Z | `d1dd1b895244` | https://geodata.ucdavis.edu/climate/worldclim/2_1/tiles/iso/KEN_wc2.1_30s_elev.tif |
| worldclim_elev_tza | - | 2026-11-12T09:36:50Z | `a27aebd529d2` | https://geodata.ucdavis.edu/climate/worldclim/2_1/tiles/iso/TZA_wc2.1_30s_elev.tif |
| worldclim_elev_uga | - | 2026-11-12T09:36:04Z | `d6cfd3c55c36` | https://geodata.ucdavis.edu/climate/worldclim/2_1/tiles/iso/UGA_wc2.1_30s_elev.tif |
| worldpop_pd_2020_eth | - | 2026-11-12T09:38:24Z | `14d6fbf32031` | https://data.worldpop.org/GIS/Population_Density/Global_2000_2020_1km_UNadj/2020/ETH/eth_pd_2020_1km_UNadj.tif |
| worldpop_pd_2020_ken | - | 2026-11-12T09:37:47Z | `0387a54db176` | https://data.worldpop.org/GIS/Population_Density/Global_2000_2020_1km_UNadj/2020/KEN/ken_pd_2020_1km_UNadj.tif |
| worldpop_pd_2020_tza | - | 2026-11-12T09:38:05Z | `b38dd332e264` | https://data.worldpop.org/GIS/Population_Density/Global_2000_2020_1km_UNadj/2020/TZA/tza_pd_2020_1km_UNadj.tif |
| worldpop_pd_2020_uga | - | 2026-11-12T09:37:50Z | `ce20aaa9cc13` | https://data.worldpop.org/GIS/Population_Density/Global_2000_2020_1km_UNadj/2020/UGA/uga_pd_2020_1km_UNadj.tif |
| worldpop_ppp_2020_eth | - | 2026-11-12T09:38:12Z | `588007498283` | https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj/2020/ETH/eth_ppp_2020_1km_Aggregated_UNadj.tif |
| worldpop_ppp_2020_ken | - | 2026-11-12T09:37:44Z | `e7be43987258` | https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj/2020/KEN/ken_ppp_2020_1km_Aggregated_UNadj.tif |
| worldpop_ppp_2020_tza | - | 2026-11-12T09:37:56Z | `632600caa7f8` | https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj/2020/TZA/tza_ppp_2020_1km_Aggregated_UNadj.tif |
| worldpop_ppp_2020_uga | - | 2026-11-12T09:37:48Z | `d55350c7c03e` | https://data.worldpop.org/GIS/Population/Global_2000_2020_1km_UNadj/2020/UGA/uga_ppp_2020_1km_Aggregated_UNadj.tif |
