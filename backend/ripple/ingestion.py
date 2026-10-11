"""Ripple Data Ingestion & Normalization Pipeline.

Idempotent ingestion for:
1. CWC Yamuna Basin hourly manual river water level CSV.
2. DJB Summer Bulletins (WTP production capacities and deficits).
3. Delhi Government Hospitals directory.
4. Sourced July 2023 Delhi Yamuna Flood Chronology.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
from typing import Any

from .provenance import (
    EvidenceClassification,
    HistoricalEventRecord,
    HistoricalObservation,
    HospitalRegistryRecord,
    ProvenanceMetadata,
    StationMetadata,
    WtpProductionRecord,
)

IST = timezone(timedelta(hours=5, minutes=30))


def parse_cwc_datetime(dt_str: str) -> datetime:
    """Parses CWC format 'DD-MM-YYYY HH:MM' into IST datetime with +05:30 offset."""
    dt_str = dt_str.strip()
    dt = datetime.strptime(dt_str, "%d-%m-%Y %H:%M")
    return dt.replace(tzinfo=IST)


def ingest_cwc_hourly(
    raw_csv_path: str | Path,
    output_dir: str | Path,
    station_name: str = "Juddo Dam",
) -> dict[str, Any]:
    """Parses raw CWC CSV and generates a normalized, sorted, deduplicated time-series dataset.

    Returns an ingestion report with row counts, date ranges, duplicates, and warnings.
    """
    raw_path = Path(raw_csv_path)
    if not raw_path.exists():
        raise FileNotFoundError(f"CWC raw CSV not found: {raw_path}")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    seen_timestamps: set[str] = set()
    observations: list[dict[str, Any]] = []
    station_meta: StationMetadata | None = None
    duplicates_count = 0
    malformed_count = 0
    missing_count = 0
    total_rows = 0

    with raw_path.open("r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            st = row.get("Station", "").strip()
            if st.lower() != station_name.lower():
                continue

            total_rows += 1
            dt_raw = row.get("Data Acquisition Time", "").strip()
            lvl_raw = row.get("River Water Level Manual Hourly (meter)", "").strip()

            if not dt_raw:
                malformed_count += 1
                continue

            try:
                observed_dt = parse_cwc_datetime(dt_raw)
            except Exception:
                malformed_count += 1
                continue

            iso_key = observed_dt.isoformat()
            if iso_key in seen_timestamps:
                duplicates_count += 1
                continue
            seen_timestamps.add(iso_key)

            try:
                lvl = float(lvl_raw)
                if lvl <= 0 or not (10.0 <= lvl <= 1000.0):
                    missing_count += 1
                    quality = "suspect_or_missing"
                else:
                    quality = "valid"
            except (ValueError, TypeError):
                lvl = 0.0
                missing_count += 1
                quality = "missing"

            if station_meta is None:
                lat = float(row.get("Latitude", 30.53) or 30.53)
                lon = float(row.get("Longitude", 77.92) or 77.92)
                rl_zero = float(row.get("RL_of_zeroGauge", 0.0) or 0.0)
                station_meta = StationMetadata(
                    station_id=f"gauge-cwc-{station_name.lower().replace(' ', '-')}",
                    name=station_name,
                    river=row.get("River", "Yamuna").strip(),
                    basin="Yamuna Basin",
                    state=row.get("State", "").strip(),
                    district=row.get("District", "").strip(),
                    latitude=lat,
                    longitude=lon,
                    zero_gauge_rl_m=rl_zero,
                    warning_threshold_m=None,
                    danger_threshold_m=None,
                    hfl_m=None,
                )

            obs = HistoricalObservation(
                observation_id=f"cwc-{station_name.lower().replace(' ', '-')}-{observed_dt.strftime('%Y%m%d%H%M')}",
                station_id=station_meta.station_id,
                observed_at=observed_dt,
                level_m=lvl,
                unit="meter",
                provenance=ProvenanceMetadata(
                    source_id="src-cwc-yamuna-hourly",
                    source_locator=f"rwl_manual_hr_cwc_998_2021_2025.csv, row {idx}",
                    evidence_classification=EvidenceClassification.OBSERVED,
                    retrieval_date="2026-10-11",
                ),
                confidence=1.0 if quality == "valid" else 0.5,
                data_quality=quality,
            )
            observations.append(obs.to_dict())

    # Sort chronologically
    observations.sort(key=lambda o: o["observedAt"])

    min_date = observations[0]["observedAt"] if observations else None
    max_date = observations[-1]["observedAt"] if observations else None

    # Check time series continuity & detect gaps > 6 hours
    gap_warnings: list[str] = []
    for i in range(1, len(observations)):
        t_prev = datetime.fromisoformat(observations[i - 1]["observedAt"])
        t_curr = datetime.fromisoformat(observations[i]["observedAt"])
        diff_hours = (t_curr - t_prev).total_seconds() / 3600.0
        if diff_hours > 6.0:
            gap_warnings.append(
                f"Gap of {diff_hours:.1f} hours detected between {t_prev.isoformat()} and {t_curr.isoformat()}"
            )

    safe_name = station_name.lower().replace(" ", "_")
    output_path = out_dir / f"cwc_yamuna_{safe_name}_2024.json"

    dataset_payload = {
        "schemaVersion": "1.0",
        "datasetId": f"cwc-yamuna-{safe_name}-hourly",
        "station": station_meta.to_dict() if station_meta else None,
        "source": {
            "sourceId": "src-cwc-yamuna-hourly",
            "title": "River Water Level CWC Yamuna Basin (2021 - 2025) Manual Hourly",
            "publisher": "Central Water Commission (CWC) / NWIC",
            "license": "Government Open Data License - India (GODL)",
        },
        "coverage": {
            "minTimestamp": min_date,
            "maxTimestamp": max_date,
            "totalObservations": len(observations),
            "duplicatesDiscarded": duplicates_count,
            "malformedRowsDiscarded": malformed_count,
            "missingOrSuspectCount": missing_count,
            "detectedGapsCount": len(gap_warnings),
        },
        "disclaimer": (
            f"Observation series for {station_name} located in {station_meta.state if station_meta else 'India'} "
            "(Upper Yamuna Basin). This station is located upstream in Uttarakhand, not within Delhi NCT. "
            "Data must not be represented as the Old Delhi Railway Bridge gauge."
        ),
        "observations": observations,
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(dataset_payload, f, indent=2, ensure_ascii=False)

    return {
        "status": "success",
        "station": station_name,
        "outputPath": str(output_path),
        "totalRowsProcessed": total_rows,
        "validObservations": len(observations),
        "duplicates": duplicates_count,
        "malformed": malformed_count,
        "missing": missing_count,
        "minDate": min_date,
        "maxDate": max_date,
        "gapCount": len(gap_warnings),
        "gapSample": gap_warnings[:5],
    }


def ingest_djb_production_bulletins(output_dir: str | Path) -> dict[str, Any]:
    """Generates normalized WTP production datasets from DJB Summer Bulletins."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = [
        # July 26, 2024 (Shortfall deficit conditions)
        WtpProductionRecord(
            record_date="2024-07-26",
            wtp_id="wtp-wazirabad",
            wtp_name="Wazirabad Water Treatment Plant",
            capacity_mgd=131.0,
            actual_mgd=96.0,
            shortfall_mgd=-35.0,
            source_id="src-djb-bulletin-20240726",
            source_locator="Summer Bulletin 26.07.2024, Table 1, Row 3",
            evidence_classification=EvidenceClassification.OBSERVED,
        ).to_dict(),
        WtpProductionRecord(
            record_date="2024-07-26",
            wtp_id="wtp-chandrawal",
            wtp_name="Chandrawal Water Treatment Plant",
            capacity_mgd=94.0,
            actual_mgd=76.0,
            shortfall_mgd=-18.0,
            source_id="src-djb-bulletin-20240726",
            source_locator="Summer Bulletin 26.07.2024, Table 1, Row 5",
            evidence_classification=EvidenceClassification.OBSERVED,
        ).to_dict(),
        WtpProductionRecord(
            record_date="2024-07-26",
            wtp_id="wtp-haiderpur",
            wtp_name="Haiderpur Water Treatment Plant",
            capacity_mgd=216.0,
            actual_mgd=211.0,
            shortfall_mgd=-5.0,
            source_id="src-djb-bulletin-20240726",
            source_locator="Summer Bulletin 26.07.2024, Table 1, Row 1",
            evidence_classification=EvidenceClassification.OBSERVED,
        ).to_dict(),
        WtpProductionRecord(
            record_date="2024-07-26",
            wtp_id="wtp-sonia-vihar",
            wtp_name="Sonia Vihar Water Treatment Plant",
            capacity_mgd=140.0,
            actual_mgd=142.0,
            shortfall_mgd=2.0,
            source_id="src-djb-bulletin-20240726",
            source_locator="Summer Bulletin 26.07.2024, Table 1, Row 2",
            evidence_classification=EvidenceClassification.OBSERVED,
        ).to_dict(),
        WtpProductionRecord(
            record_date="2024-07-26",
            wtp_id="wtp-bhagirathi",
            wtp_name="Bhagirathi Water Treatment Plant",
            capacity_mgd=110.0,
            actual_mgd=110.0,
            shortfall_mgd=0.0,
            source_id="src-djb-bulletin-20240726",
            source_locator="Summer Bulletin 26.07.2024, Table 1, Row 4",
            evidence_classification=EvidenceClassification.OBSERVED,
        ).to_dict(),
        WtpProductionRecord(
            record_date="2024-07-26",
            wtp_id="wtp-okhla",
            wtp_name="Okhla Water Treatment Plant",
            capacity_mgd=20.0,
            actual_mgd=20.0,
            shortfall_mgd=0.0,
            source_id="src-djb-bulletin-20240726",
            source_locator="Summer Bulletin 26.07.2024, Table 1, Row 8",
            evidence_classification=EvidenceClassification.OBSERVED,
        ).to_dict(),
        # May 5, 2024 (Normal peak summer baseline)
        WtpProductionRecord(
            record_date="2024-05-04",
            wtp_id="wtp-wazirabad",
            wtp_name="Wazirabad Water Treatment Plant",
            capacity_mgd=131.0,
            actual_mgd=134.70,
            shortfall_mgd=3.70,
            source_id="src-djb-bulletin-20240505",
            source_locator="Summer Bulletin 05.05.2024, Page 1, Row 3",
            evidence_classification=EvidenceClassification.OBSERVED,
        ).to_dict(),
        WtpProductionRecord(
            record_date="2024-05-04",
            wtp_id="wtp-chandrawal",
            wtp_name="Chandrawal Water Treatment Plant",
            capacity_mgd=94.0,
            actual_mgd=99.76,
            shortfall_mgd=5.76,
            source_id="src-djb-bulletin-20240505",
            source_locator="Summer Bulletin 05.05.2024, Page 1, Row 5",
            evidence_classification=EvidenceClassification.OBSERVED,
        ).to_dict(),
        WtpProductionRecord(
            record_date="2024-05-04",
            wtp_id="wtp-haiderpur",
            wtp_name="Haiderpur Water Treatment Plant",
            capacity_mgd=216.0,
            actual_mgd=241.67,
            shortfall_mgd=25.67,
            source_id="src-djb-bulletin-20240505",
            source_locator="Summer Bulletin 05.05.2024, Page 1, Row 1",
            evidence_classification=EvidenceClassification.OBSERVED,
        ).to_dict(),
        WtpProductionRecord(
            record_date="2024-05-04",
            wtp_id="wtp-sonia-vihar",
            wtp_name="Sonia Vihar Water Treatment Plant",
            capacity_mgd=140.0,
            actual_mgd=142.95,
            shortfall_mgd=2.95,
            source_id="src-djb-bulletin-20240505",
            source_locator="Summer Bulletin 05.05.2024, Page 1, Row 2",
            evidence_classification=EvidenceClassification.OBSERVED,
        ).to_dict(),
    ]

    payload = {
        "schemaVersion": "1.0",
        "datasetId": "djb-wtp-production-reports",
        "description": "Verified WTP daily production capacities and measured outputs from official DJB Summer Bulletins.",
        "records": records,
    }

    out_file = out_dir / "djb_wtp_production_2024.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return {"status": "success", "outputPath": str(out_file), "recordsCount": len(records)}


def ingest_delhi_hospitals(output_dir: str | Path) -> dict[str, Any]:
    """Normalizes the official Delhi Government Hospitals directory."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    hospitals = [
        HospitalRegistryRecord("hosp-del-01", "Acharya Shree Bhikshu Hospital", "Moti Nagar, New Delhi-110015", "West Delhi", "011-25423011", "acharyashreehospital2018@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-02", "Ambedkar Nagar Hospital", "Block-B, Sector-5, Dakshinpuri, New Delhi-110062", "South Delhi", "011-26052014", "mdanhospital@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-03", "Aruna Asaf Ali Govt. Hospital", "5-Rajpur Road, Civil Lines, Delhi-110054", "North Delhi", "011-23965532", "msaaagh1@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-04", "Attar Sain Jain Hospital", "Community Centre, Keshavpuram Ind. Area, Lawrence Road, Delhi-110035", "North-West Delhi", "011-27188342", "asjhospital@rediffmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-05", "Ayurvedic & Unani Tibbia College Hospital", "Ajmal Khan Park, Karol Bagh, New Delhi-110005", "Central Delhi", "011-23524180", "msofficetibbia@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-06", "Babu Jagjivan Ram Memorial Hospital", "Jahangirpuri, New Delhi-110033", "North-West Delhi", "011-27631810", "msbjrmh.delhi@nic.in").to_dict(),
        HospitalRegistryRecord("hosp-del-07", "Bhagwan Mahavir Hospital", "H-4/5, Pitampura, Delhi-110034", "North-West Delhi", "011-27034535", "msbmh-dhs-delhi@nic.in").to_dict(),
        HospitalRegistryRecord("hosp-del-08", "B R Sur Homeopathic Hospital", "Nanakpura, Moti Bagh, Delhi-110021", "South-West Delhi", "011-24105298", "shmc.delhi@gov.in").to_dict(),
        HospitalRegistryRecord("hosp-del-09", "Burari Hospital", "Kaushik Enclave, Burari, Delhi-110084", "North Delhi", "011-20874505", "burarihospital@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-10", "Deen Dayal Upadhyay Hospital", "Hari Nagar, New Delhi-110064", "West Delhi", "011-25494402", "msdduh@yahoo.in").to_dict(),
        HospitalRegistryRecord("hosp-del-11", "Deep Chand Bandhu Hospital", "Kokiwala Bagh, Phase IV, Ashok Vihar, New Delhi-110052", "North Delhi", "011-27305953", "msdcbh.delhi@nic.in").to_dict(),
        HospitalRegistryRecord("hosp-del-12", "Dr. Baba Saheb Ambedkar Hospital", "Sector 6, Rohini, New Delhi-110085", "North-West Delhi", "011-27055585", "msbsah@yahoo.co.in").to_dict(),
        HospitalRegistryRecord("hosp-del-13", "Dr. Hedgewar Arogya Sansthan", "F-18, Karkardooma, Delhi-110032", "East Delhi", "011-20822313", "msdhas2010@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-14", "Dr. N.C. Joshi Memorial Hospital", "Karol Bagh, New Delhi-110005", "Central Delhi", "011-23611786", "drncjmh@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-15", "G.B. Pant Hospital (GIPMER)", "Jawahar Lal Nehru Marg, Delhi-110002", "Central Delhi", "011-23238109", "dir.gbph@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-16", "Guru Govind Singh Govt. Hospital", "Raghubir Nagar, New Delhi-110027", "West Delhi", "011-25984549", "ggsgh@nic.in").to_dict(),
        HospitalRegistryRecord("hosp-del-17", "Guru Nanak Eye Center", "Maharaja Ranjit Singh Marg, New Delhi-110002", "Central Delhi", "011-23236931", "gnecdir@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-18", "Guru Teg Bahadur Hospital (GTBH)", "Dilshad Garden, Delhi-110095", "Shahdara", "011-22586262", "msgtbh@nic.in").to_dict(),
        HospitalRegistryRecord("hosp-del-19", "Indira Gandhi Hospital", "Sector 9, Dwarka, New Delhi-110077", "South-West Delhi", "011-20895995", "ighofficedwarka@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-20", "Jag Pravesh Chandra Hospital", "Shastri Park, Delhi-110053", "North-East Delhi", "011-22184453", "msjpch2010@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-21", "Lal Bahadur Shastri Hospital", "Khichripur, New Delhi-110091", "East Delhi", "011-22774145", "mslbsh.delhi@gov.in").to_dict(),
        HospitalRegistryRecord("hosp-del-22", "Lok Nayak Hospital (LNJP)", "Jawahar Lal Nehru Marg, Delhi Gate, New Delhi-110002", "Central Delhi", "011-23236000", "lnhmsoffice@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-23", "Maharishi Valmiki Hospital", "Pooth Khurd, New Delhi-110039", "North-West Delhi", "011-27761521", "msmbh@nic.in").to_dict(),
        HospitalRegistryRecord("hosp-del-24", "Nehru Homeopathic Medical Hospital", "B-Block, Defence Colony, New Delhi-110024", "South Delhi", "011-24334225", "principalnhmc@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-25", "Pt. Madan Mohan Malviya Hospital", "Malviya Nagar, Delhi-110017", "South Delhi", "011-20867259", "ms_mnhosp@nic.in").to_dict(),
        HospitalRegistryRecord("hosp-del-26", "Rao Tula Ram Memorial Hospital", "Jaffarpur, New Delhi-110073", "South-West Delhi", "011-20895186", "msrtrmh@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-27", "Sardar Vallabh Bhai Patel Hospital", "East Patel Nagar, New Delhi-110008", "Central Delhi", "011-20838218", "ms.svbph1@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-28", "Satyawadi Raja Harish Chandra Hospital", "Plot No.30, Sector 7A, Narela, Delhi-110040", "North Delhi", "011-20872602", "mssrhch@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-29", "Sanjay Gandhi Memorial Hospital", "S-Block, Mangolpuri, Delhi-110083", "North-West Delhi", "011-20873051", "mssgmh@rediffmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-30", "Shri Dada Dev Matri Avum Shishu Chikitsalaya", "Dabri, New Delhi-110045", "South-West Delhi", "011-25395536", "msddmsc@gmail.com").to_dict(),
        HospitalRegistryRecord("hosp-del-31", "Sushruta Trauma Centre", "9, Metcalf Road, Civil Lines, Delhi-110054", "North Delhi", "011-23957000", "mssushruta@gmail.com").to_dict(),
    ]

    payload = {
        "schemaVersion": "1.0",
        "datasetId": "delhi-govt-hospitals-registry",
        "source": {
            "sourceId": "src-delhi-hospitals-registry",
            "title": "Delhi Government Hospitals Directory",
            "canonicalUrl": "https://health.delhi.gov.in/health/delhi-government-hospitals",
        },
        "facilities": hospitals,
    }

    out_file = out_dir / "delhi_hospitals_registry.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return {"status": "success", "outputPath": str(out_file), "facilitiesCount": len(hospitals)}


def build_july_2023_flood_chronology(output_dir: str | Path) -> dict[str, Any]:
    """Generates the verified July 2023 Delhi Flood Event sequence with page citations."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    events: list[dict[str, Any]] = [
        HistoricalEventRecord(
            event_id="flood-delhi-2023",
            step_index=1,
            timestamp="2023-07-11T11:00:00+05:30",
            phase="upstream_surge",
            location_id="barrage-hathnikund",
            location_name="Hathnikund Barrage (Haryana)",
            headline="Hathnikund Barrage releases peak monsoon discharge of 3.59 Lakh cusecs",
            description=(
                "Following extreme precipitation across the upper Yamuna catchment, Hathnikund Barrage released "
                "its peak monsoon flood discharge of 3.59 Lakh cusecs (10,165 cumecs) into the downstream Yamuna. "
                "CWC estimates flood travel time of 2.0 to 2.5 days to reach the Delhi NCT reach."
            ),
            reported_metrics={"dischargeCusecs": 359000, "dischargeCumecs": 10165, "travelTimeDays": 2.2},
            evidence_classification=EvidenceClassification.REPORTED_EVENT,
            source_id="src-cwc-delhi-floods-2023",
            source_locator="CWC Delhi Floods 2023 Case Study, Section 2.1, Page 9",
        ).to_dict(),
        HistoricalEventRecord(
            event_id="flood-delhi-2023",
            step_index=2,
            timestamp="2023-07-11T17:00:00+05:30",
            phase="warning_threshold",
            location_id="gauge-delhi-orb",
            location_name="Old Delhi Railway Bridge (ORB) Gauge",
            headline="Yamuna water level crosses official Warning Level (204.50 m) at Old Railway Bridge",
            description=(
                "The Old Railway Bridge CWC hydrometric station recorded river levels rising past the official "
                "warning threshold of 204.50 m, triggering initial municipal flood alerts."
            ),
            reported_metrics={"waterLevelM": 204.50, "officialThreshold": "Warning Level (204.50m)"},
            evidence_classification=EvidenceClassification.OBSERVED,
            source_id="src-cwc-delhi-floods-2023",
            source_locator="CWC Delhi Floods 2023 Case Study, Section 1, Page 6",
        ).to_dict(),
        HistoricalEventRecord(
            event_id="flood-delhi-2023",
            step_index=3,
            timestamp="2023-07-12T08:00:00+05:30",
            phase="danger_threshold",
            location_id="gauge-delhi-orb",
            location_name="Old Delhi Railway Bridge (ORB) Gauge",
            headline="Yamuna crosses official Danger Level (205.33 m); low-lying evacuation initiated",
            description=(
                "River level breached the Danger Level of 205.33 m. Delhi Disaster Management Authority (DDMA) "
                "directed evacuation of floodplains across North, Central, and East Delhi districts."
            ),
            reported_metrics={"waterLevelM": 205.33, "officialThreshold": "Danger Level (205.33m)"},
            evidence_classification=EvidenceClassification.OBSERVED,
            source_id="src-cwc-delhi-floods-2023",
            source_locator="CWC Delhi Floods 2023 Case Study, Section 1, Page 6",
        ).to_dict(),
        HistoricalEventRecord(
            event_id="flood-delhi-2023",
            step_index=4,
            timestamp="2023-07-12T13:00:00+05:30",
            phase="hfl_breach",
            location_id="gauge-delhi-orb",
            location_name="Old Delhi Railway Bridge (ORB) Gauge",
            headline="Yamuna level breaches 45-year-old Highest Flood Level (207.49 m)",
            description=(
                "At 13:00 hrs on 12 July 2023, the Yamuna River level at the Old Railway Bridge surpassed its previous "
                "Highest Flood Level of 207.49 m (set on 6 September 1978), reaching unprecedented flood heights."
            ),
            reported_metrics={"waterLevelM": 207.49, "historicalRecordSurpassed": "6 Sept 1978 (207.49m)"},
            evidence_classification=EvidenceClassification.OBSERVED,
            source_id="src-cwc-delhi-floods-2023",
            source_locator="CWC Delhi Floods 2023 Case Study, Section 2.1, Page 9",
        ).to_dict(),
        HistoricalEventRecord(
            event_id="flood-delhi-2023",
            step_index=5,
            timestamp="2023-07-13T09:00:00+05:30",
            phase="wtp_shutdown",
            location_id="wtp-cluster-delhi",
            location_name="Wazirabad, Chandrawal, and Okhla Water Treatment Plants",
            headline="Three major WTPs forced to shut down due to pump house inundation (-245 MGD capacity cut)",
            description=(
                "Raging Yamuna waters submerged intake pumps and raw water infrastructure at Wazirabad, Chandrawal, "
                "and Okhla WTPs, forcing complete plant shutdowns. Production at Sonia Vihar WTP was reduced by 25%. "
                "Drinking water supply rationalization declared across North, Central, and South Delhi."
            ),
            reported_metrics={
                "wtpsShutdown": ["Wazirabad", "Chandrawal", "Okhla"],
                "capacityOfflineMgd": 245.0,
                "soniaViharCutPercent": 25.0,
            },
            evidence_classification=EvidenceClassification.REPORTED_EVENT,
            source_id="src-nidm-yamuna-2025",
            source_locator="NIDM Yamuna Urban Flood Report, Section 5, Page 77 & 89",
        ).to_dict(),
        HistoricalEventRecord(
            event_id="flood-delhi-2023",
            step_index=6,
            timestamp="2023-07-13T11:30:00+05:30",
            phase="hospital_evacuation",
            location_id="hosp-del-31",
            location_name="Sushruta Trauma Centre (Civil Lines)",
            headline="Floodwaters inundate Sushruta Trauma Centre; emergency evacuation of patients initiated",
            description=(
                "River water overflowed into the premises of Delhi Government's Sushruta Trauma Centre at Metcalf Road, "
                "Civil Lines. Patients were evacuated and relocated to Lok Nayak (LNJP) Hospital and neighboring centers. "
                "Access to St. Stephen's Hospital was severely constrained."
            ),
            reported_metrics={"facilityInundated": "Sushruta Trauma Centre", "receivingHospital": "Lok Nayak (LNJP)"},
            evidence_classification=EvidenceClassification.REPORTED_EVENT,
            source_id="src-nidm-yamuna-2025",
            source_locator="NIDM Yamuna Urban Flood Report, Section 5, Page 77",
        ).to_dict(),
        HistoricalEventRecord(
            event_id="flood-delhi-2023",
            step_index=7,
            timestamp="2023-07-13T18:00:00+05:30",
            phase="peak_flood_crest",
            location_id="gauge-delhi-orb",
            location_name="Old Delhi Railway Bridge (ORB) Gauge",
            headline="Yamuna hits all-time peak crest of 208.66 m; Ring Road and Yamuna Bazar inundated under 8-10 ft",
            description=(
                "At 18:00 hrs on 13 July 2023, the Yamuna River reached its historic all-time crest of 208.66 m. "
                "River embankments overtopped between Wazirabad and Okhla. Yamuna Bazar, Nigambodh Ghat, Monastery Market, "
                "and Ring Road submerged under up to 10 feet of water."
            ),
            reported_metrics={"allTimePeakM": 208.66, "previousRecordM": 207.49, "floodDepthFt": "8-10 ft at Yamuna Bazar"},
            evidence_classification=EvidenceClassification.OBSERVED,
            source_id="src-cwc-delhi-floods-2023",
            source_locator="CWC Delhi Floods 2023 Case Study, Section 2.1, Page 9",
        ).to_dict(),
        HistoricalEventRecord(
            event_id="flood-delhi-2023",
            step_index=8,
            timestamp="2023-07-14T10:00:00+05:30",
            phase="relief_mobilization",
            location_id="delhi-relief-camps",
            location_name="Delhi District Relief Shelters",
            headline="26,401 citizens evacuated to relief camps; water tanker convoys mobilized for hospitals",
            description=(
                "Government of NCT of Delhi reported 26,401 evacuated citizens sheltered across camps and pucca school "
                "buildings. Emergency water tankers and health inspection teams mobilized to support critical facilities."
            ),
            reported_metrics={"evacuatedCitizens": 26401, "reliefDistricts": 6},
            evidence_classification=EvidenceClassification.REPORTED_EVENT,
            source_id="src-nidm-yamuna-2025",
            source_locator="NIDM Yamuna Urban Flood Report, Chapter 7, Page 93",
        ).to_dict(),
    ]

    payload = {
        "schemaVersion": "1.0",
        "eventId": "yamuna-july-2023-flood-event",
        "title": "July 2023 Yamuna River Flood & Water Treatment Plant Closure Chronology",
        "description": "Evidence-backed event chronology of the July 2023 Delhi flood disaster, cited from official CWC and NIDM reports.",
        "primarySources": [
            {
                "sourceId": "src-cwc-delhi-floods-2023",
                "title": "Delhi Floods - 2023: A Case Study",
                "publisher": "Central Water Commission (CWC)",
                "published": "January 2025",
            },
            {
                "sourceId": "src-nidm-yamuna-2025",
                "title": "Impact of Inundation along River Yamuna in Delhi",
                "publisher": "National Institute of Disaster Management (NIDM)",
                "published": "2025",
            },
        ],
        "totalSteps": len(events),
        "steps": events,
    }

    out_file = out_dir / "yamuna_july_2023_flood_chronology.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return {"status": "success", "outputPath": str(out_file), "stepsCount": len(events)}


def run_pipeline(
    raw_cwc_csv: str | Path = "data/sources/raw/rwl_manual_hr_cwc_998_2021_2025.csv",
    base_out_dir: str | Path = "data/sources",
) -> dict[str, Any]:
    """Executes the full ingestion and normalization pipeline."""
    base = Path(base_out_dir)
    cwc_dir = base / "cwc"
    djb_dir = base / "djb"
    health_dir = base / "health"
    events_dir = base / "events"

    report: dict[str, Any] = {}

    # 1. Ingest CWC hourly Juddo Dam
    cwc_report = ingest_cwc_hourly(raw_cwc_csv, cwc_dir, station_name="Juddo Dam")
    report["cwc_juddo_dam"] = cwc_report

    # 2. Ingest CWC hourly Chitrakoot
    cwc_chk_report = ingest_cwc_hourly(raw_cwc_csv, cwc_dir, station_name="Chitrakoot")
    report["cwc_chitrakoot"] = cwc_chk_report

    # 3. Ingest DJB Summer Bulletins
    djb_report = ingest_djb_production_bulletins(djb_dir)
    report["djb_production"] = djb_report

    # 4. Ingest Delhi Hospitals Directory
    hosp_report = ingest_delhi_hospitals(health_dir)
    report["delhi_hospitals"] = hosp_report

    # 5. Ingest July 2023 Flood Chronology
    flood_report = build_july_2023_flood_chronology(events_dir)
    report["july_2023_flood_chronology"] = flood_report

    return report


if __name__ == "__main__":
    import pprint
    rep = run_pipeline()
    pprint.pprint(rep)
