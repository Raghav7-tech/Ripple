# Ripple Source Material Inventory & Audit Report

This document records the provenance, audit findings, structural schema, geographic scope, and operational limitations of all primary and secondary data sources evaluated for Ripple's evidence-backed historical replay platform.

Audit Date: 11 October 2026  
Status: Verified & Documented  
Classification Standard:
- `observed`: Direct empirical measurement or telemetry record from an instrumented sensor or official log.
- `reported_event`: Explicitly documented historical incident, government situation report (SITREP), or official press announcement.
- `derived`: Calculated from documented source-backed inputs using a cited, published mathematical formula.
- `assumed`: Hypothesized cascade connection, default propagation delay, or parameter without direct empirical measurement.
- `synthetic`: Artificial walk-through or test-fixture data generated purely for testing or interface demonstrations.

---

## Source Inventory Summary

| Source ID | Publisher | Title | Format | Status | Usable for Ripple |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `src-cwc-yamuna-hourly` | Central Water Commission (CWC) / NWIC | River Water Level CWC Yamuna Basin (2021-2025) Manual Hourly | CSV (2.78 MB) | Downloaded & Parsed | Upper Yamuna hydrological time series (Juddo Dam & Chitrakoot stations, 2024–2025) |
| `src-djb-bulletin-20240726` | Delhi Jal Board (DJB) | Summer Bulletin dated 26.07.2024 | PDF (1 page) | Downloaded & Parsed | WTP-wise production capacities, actual outputs, and shortfall measurements |
| `src-djb-bulletin-20240505` | Delhi Jal Board (DJB) | Summer Bulletin dated 05.05.2024 | PDF (2 pages) | Downloaded & Parsed | Peak summer baseline production (1004 MGD) and 1916 CRM complaint volume |
| `src-djb-press-releases` | Delhi Jal Board (DJB) | DJB Official Press Releases & Outage Notices | HTML & PDF | Inspected & Cataloged | Scheduled maintenance outage announcements and localized water rationing notices |
| `src-delhi-hospitals-registry` | Department of Health & Family Welfare, Govt. of NCT of Delhi | Delhi Government Hospitals Official Directory | HTML Table | Downloaded & Parsed | Verified directory of 31 Delhi government hospitals with names and addresses |
| `src-mohfw-iphs-guidelines` | Ministry of Health & Family Welfare (MoHFW) | Indian Public Health Standards (IPHS) Guidelines for District Hospitals | PDF (124 pages) | Downloaded & Parsed | Official engineering proxy norm for hospital water demand (450–500 L/bed/day) |
| `src-cwc-delhi-floods-2023` | Central Water Commission (CWC), Hydrology (Urban) Directorate | Delhi Floods - 2023: A Case Study (Pub. Jan 2025) | PDF (41 pages) | Downloaded & Parsed | Official flood timeline, peak gauge level (208.66m at ORB), and Hathnikund discharge |
| `src-nidm-yamuna-2025` | National Institute of Disaster Management (NIDM) | Impact of Inundation along River Yamuna in Delhi (Pub. 2025) | PDF (116 pages) | Downloaded & Parsed | WTP inundation closures (Wazirabad, Chandrawal, Okhla), hospital evacuation, flood impacts |

---

## Detailed Source Audits

### 1. `src-cwc-yamuna-hourly`: CWC Yamuna Basin Hourly River Water Level

- **Publisher**: Central Water Commission (CWC), Ministry of Jal Shakti, Government of India.
- **Portal**: National Water Data Portal (NWIC).
- **Canonical URL**: `https://nwdp.nwic.gov.in/dataset/river-water-level-manual-hourly-cwc-subernarekha/resource/dd3b9bba-6ba2-4954-93cf-e3ee84b5d9af`
- **Direct Download URL**: `https://nwdp.nwic.gov.in/dataset/d951a09c-6cf8-470e-be77-e80116f13d34/resource/dd3b9bba-6ba2-4954-93cf-e3ee84b5d9af/download/rwl_manual_hr_cwc_998_2021_2025.csv`
- **Access Date**: 11 October 2026
- **License**: Government Open Data License - India (GODL).
- **Format**: CSV, 2,784,613 bytes, 15,963 lines (including header).
- **SHA-256**: `4adaf0a8de9aa6588971420d4b18ec0920ad2c58e8eab6a0bea10134ae37a8e9`
- **Columns**: `SlNo`, `Station`, `Agency`, `State LGD Code`, `State`, `District LGD Code`, `District`, `Tehsil`, `Block`, `Village`, `River`, `Basin`, `Tributary`, `Subtributary`, `SubSubtributary`, `Local River`, `Latitude`, `Longitude`, `Is_DischargeDataAvailable`, `RL_of_zeroGauge`, `MeanSeaLevel`, `Data Acquisition Time`, `River Water Level Manual Hourly (meter)`.

#### Critical Audit Findings & Scope
1. **Catalog Path vs Resource Content**: The URL slug contains `/subernarekha/` due to a catalog naming defect in the NWIC CKAN portal. However, verification of the downloaded file header and metadata confirms that the dataset contains `Basin = "Yamuna Basin"`.
2. **Station Coverage**: The dataset contains 15,962 observation rows across exactly **2 observation stations**:
   - **Station 1: `Juddo Dam`**: Uttarakhand, District Dehradun, Tehsil Chakrata. Coordinates: `30.53°N, 77.92°E`. River: Yamuna (Upper Yamuna mainstem/tributary). Coverage: `01-06-2024 12:00` to `31-12-2025 18:00` (7,827 rows).
   - **Station 2: `Chitrakoot`**: Madhya Pradesh, District Satna, Tehsil Majhgawan. Coordinates: `25.14°N, 80.85°E`. River: Yamuna (Mandakini/Paisuni Yamuna subbasin). Coverage: `01-01-2024 08:00` to `26-12-2025 08:00` (8,135 rows).
3. **Absence of Delhi City Gauges in this File**: This specific NWIC resource **does not contain the Old Delhi Railway Bridge (ORB) or Okhla Barrage gauges**, nor does it cover July 2023. It contains verified 2024–2025 measurements for the Upper Yamuna Basin.
4. **Usage in Ripple**:
   - `Juddo Dam` provides an authentic, verified hourly river observation series for historical hydrological replay in the Upper Yamuna Basin.
   - Ripple discloses that `Juddo Dam` is located in Dehradun, Uttarakhand, and does not claim it is located within Delhi NCT.
   - Units: `River Water Level Manual Hourly (meter)` is normalized to meters above sea level (`RL_of_zeroGauge + gauge_height` where applicable).
   - Timestamps: Formatted as `DD-MM-YYYY HH:MM` and normalized to ISO 8601 strings in Indian Standard Time (`+05:30`).

---

### 2. `src-djb-bulletin-20240726`: DJB Summer Bulletin 26 July 2024

- **Publisher**: Delhi Jal Board, Government of NCT of Delhi.
- **Canonical URL**: `https://delhijalboard.delhi.gov.in/sites/default/files/Jalboard/universal-tab/summer_bulletin_26.07.2024_1.pdf`
- **Access Date**: 11 October 2026
- **Format**: PDF (1 page, 2,412,704 bytes).
- **Usable Evidence**: Direct empirical reporting of citywide and facility-level water production on 26 July 2024.
- **Key Facts Extracted**:
  - Total Citywide Water Production: **904 MGD** (reported shortfall of **52 MGD** against 956 MGD design capacity).
  - Facility-specific production breakdown:
    - `Wazirabad WTP`: Design Capacity **131 MGD**, Actual Production **96 MGD** (reported shortfall: **-35 MGD**).
    - `Chandrawal WTP`: Design Capacity **94 MGD**, Actual Production **76 MGD** (reported shortfall: **-18 MGD**).
    - `Haiderpur WTP`: Design Capacity **216 MGD**, Actual Production **211 MGD** (reported shortfall: **-5 MGD**).
    - `Sonia Vihar WTP`: Design Capacity **140 MGD**, Actual Production **142 MGD** (normal).
    - `Bhagirathi WTP`: Design Capacity **110 MGD**, Actual Production **110 MGD** (normal).
    - `Dwarka WTP`: Design Capacity **50 MGD**, Actual Production **52 MGD** (normal).
    - `Nangloi WTP`: Design Capacity **40 MGD**, Actual Production **42 MGD** (normal).
    - `Okhla WTP`: Design Capacity **20 MGD**, Actual Production **20 MGD** (normal).
- **Limitations**: Daily aggregate only. Does not break down production by hour or trace which specific service pipes received reduced pressure.

---

### 3. `src-djb-bulletin-20240505`: DJB Summer Bulletin 5 May 2024

- **Publisher**: Delhi Jal Board, Government of NCT of Delhi.
- **Canonical URL**: `https://delhijalboard.delhi.gov.in/sites/default/files/Jalboard/universal-tab/summer_bulletin_05.05.2024.pdf`
- **Access Date**: 11 October 2026
- **Format**: PDF (2 pages, 5,647,766 bytes).
- **Usable Evidence**: Baseline peak summer operational conditions (Situation Report for 04.05.2024) and municipal CRM distress call volume.
- **Key Facts Extracted**:
  - Total Citywide Water Production: **1004.31 MGD** (operating at 105% of rated capacity).
  - WTP breakdown: Wazirabad (134.7 MGD), Chandrawal (99.76 MGD), Haiderpur (241.67 MGD), Sonia Vihar (142.95 MGD).
  - CRM 1916 Helpline Complaints (Page 2): 528 water complaints, 106 water tanker requests, 437 sewer complaints registered in 24 hours.
- **Usage in Ripple**: Establishes standard non-flood summer operational baseline to contrast against flood-disrupted and dry-season shortfall scenarios.

---

### 4. `src-delhi-hospitals-registry`: Delhi Government Hospitals Directory

- **Publisher**: Department of Health & Family Welfare, Government of NCT of Delhi.
- **Canonical URL**: `https://health.delhi.gov.in/health/delhi-government-hospitals`
- **Access Date**: 11 October 2026
- **Format**: Structured HTML Table (31 facilities).
- **Usable Evidence**: Official facility registry containing hospital names, full street addresses, contact phone numbers, and official emails.
- **Key Facilities in Cascade Impact Reach**:
  - `Aruna Asaf Ali Govt. Hospital`: 5-Rajpur Road, Civil Lines, Delhi-110054 (Zone: North Delhi / Civil Lines; fed by Wazirabad/Chandrawal distribution network).
  - `Sushruta Trauma Centre`: 9-Metcalf Road, Civil Lines, Delhi-110054 (located on Yamuna riverfront, directly inundated in July 2023).
  - `Lok Nayak Hospital (LNJP)`: Jawahar Lal Nehru Marg, Delhi Gate, New Delhi-110002 (Central Delhi; major referral center).
  - `G.B. Pant Hospital (GIPMER)`: Jawahar Lal Nehru Marg, Delhi-110002 (Central Delhi super-specialty).
  - `Burari Hospital`: Kaushik Enclave, Burari, Delhi-110084 (North Delhi floodplain perimeter).
  - `Babu Jagjivan Ram Memorial Hospital`: Jahangirpuri, New Delhi-110033 (North-West Delhi).
- **Limitations**: Does not provide latitude/longitude coordinates or exact bed census. Coordinates require explicit geocoding enrichment with documented source notes.

---

### 5. `src-mohfw-iphs-guidelines`: MoHFW Indian Public Health Standards

- **Publisher**: Ministry of Health & Family Welfare, Government of India.
- **Canonical URL**: `https://clinicalestablishments.mohfw.gov.in/sites/default/files/2021-12/108.pdf`
- **Document**: *Indian Public Health Standards (IPHS): Guidelines for District Hospitals (101 to 500 Bedded)*.
- **Access Date**: 11 October 2026
- **Format**: PDF (124 pages, 1,853,850 bytes).
- **Usable Evidence**: Section on Engineering and Water Supply Services (Page 47).
- **Exact Official Norm**:
  > *"Water requirement per bed per day = 450 to 500 litres"* (Page 47)
  > Overhead storage requirement: Minimum 48 hours buffer recommended for clinical continuity.
- **Usage in Ripple**: Enables transparent derivation of hospital daily water demand proxy based on bed capacity.
  - Formula: $\text{Daily Water Demand (L/day)} = \text{Bed Count} \times 475\text{ L/bed/day}$.
  - Classification: `derived` (using official MoHFW norm, but Bed Count may be an estimated proxy if facility-specific audited census is unavailable).

---

### 6. `src-cwc-delhi-floods-2023`: CWC Delhi Floods 2023 Case Study

- **Publisher**: Central Water Commission (CWC), Hydrology (Urban) Directorate, New Delhi.
- **Publication Number**: `CWC/2025/01` (January 2025).
- **Canonical URL**: `https://cwc.gov.in/sites/default/files/delhi-floods-2023-case-study.pdf`
- **Access Date**: 11 October 2026
- **Format**: PDF (41 pages, 3,557,366 bytes).
- **Key Facts Extracted with Page Citations**:
  - **Warning Level at Old Railway Bridge (ORB)**: **204.50 m** (Page 6).
  - **Danger Level at Old Railway Bridge (ORB)**: **205.33 m** (Page 6).
  - **Previous Highest Flood Level (HFL)**: **207.49 m** (recorded on 6 September 1978) (Page 9).
  - **Old Railway Bridge Girder Bottom**: **207.40 m** (Page 6).
  - **Hathnikund Barrage Peak Discharge**: **3.59 Lakh cusecs (10,165 cumec)** released at **11:00 hrs on 11 July 2023** (Page 9).
  - **Flood Travel Time from Hathnikund to Delhi**: **2.0 to 2.5 days (48 to 60 hours)** (Page 8).
  - **Crossing of Previous HFL (207.49 m)**: **13:00 hrs on 12 July 2023** (Page 9).
  - **All-Time Peak Water Level Recorded**: **208.66 m at 18:00 hrs on 13 July 2023** (Page 9).
  - **Floodplain Reach**: Overtopping of embankments between Wazirabad Barrage and Okhla Barrage (Page 9).

---

### 7. `src-nidm-yamuna-2025`: NIDM Yamuna Inundation Impact Report

- **Publisher**: National Institute of Disaster Management (NIDM), Ministry of Home Affairs.
- **Title**: *Impact of Inundation along River Yamuna in Delhi* (2025).
- **Canonical URL**: `https://nidm.gov.in/PDF/pubs/Yamuna_2025.pdf`
- **Access Date**: 11 October 2026
- **Format**: PDF (116 pages, 19,333,803 bytes).
- **Key Facts Extracted with Page Citations**:
  - **Water Treatment Plant Inundation & Shutdown**: On **Thursday, 13 July 2023**, floodwaters submerged intake pumps, causing the immediate shutdown of **three major WTPs: Wazirabad, Chandrawal, and Okhla** (Page 77).
  - **Sonia Vihar Reduction**: Production at Sonia Vihar WTP reduced by **25%** due to pipeline backflow (Page 73, Page 77).
  - **Tubewell Disruption**: Submerged riverbed tubewells disabled across North and Central Delhi (Page 77).
  - **Healthcare Facility Inundation**: Floodwaters gushed into the premises of Delhi Government's **Sushruta Trauma Centre** (Civil Lines) on 13 July 2023, forcing the emergency evacuation of patients to LNJP and other hospitals (Page 77).
  - **Hospital Alert Status**: Lal Bahadur Shastri (LBS) Hospital and Chacha Nehru Bal Chikitsalaya (CNBC) placed on high alert (Page 87).
  - **Evacuation Scale**: Approximately **26,401 citizens** evacuated from low-lying areas across 6 districts to emergency relief shelters (Page 93).
  - **Municipal Rationalization**: Delhi Jal Board implemented emergency water rationing across North, Central, and South Delhi (Page 89).

---

## Provenance Enforcement Rules for Ripple

1. **No Conflation of River Reach with City Stations**: CWC hourly readings from Juddo Dam (Uttarakhand) are explicitly presented with their Dehradun location and cannot be labeled as Delhi Railway Bridge gauge readings.
2. **Reported Chronology vs Continuous Telemetry**: The July 2023 flood disaster is structured as a verified report chronology (sourced from CWC and NIDM) rather than synthesized as an artificial 1-minute gauge time-series.
3. **Transparent Operational Assumptions**:
   - The hydraulic link between Wazirabad WTP disruption and North Delhi hospitals is modeled using Ripple's deterministic graph traversal with explicitly labeled assumptions (`assumed`).
   - Hospital demand is derived using the MoHFW 475 L/bed/day formula (`derived`) with bed census notes.
4. **Idempotence & Traceability**: All normalized JSON datasets in `data/sources/` cite the exact source ID, locator (page/table/row), and processing timestamp.
