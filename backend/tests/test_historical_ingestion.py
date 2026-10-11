"""Tests for Ripple Ingestion, Provenance, and Historical Replay."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
import unittest

from ripple.historical_replay import (
    HospitalDemandCalculator,
    build_historical_yamuna_2023_scenario,
    get_cwc_observations,
    get_delhi_hospitals,
    get_djb_production_records,
    get_july_2023_flood_chronology,
)
from ripple.ingestion import ingest_cwc_hourly, parse_cwc_datetime
from ripple.models import DependencyGraph, Observation
from ripple.provenance import (
    EvidenceClassification,
    HistoricalEventRecord,
    HistoricalObservation,
    ProvenanceMetadata,
    StationMetadata,
)
from ripple.replay import run_replay

IST = timezone(timedelta(hours=5, minutes=30))


class IngestionAndProvenanceTests(unittest.TestCase):
    def test_cwc_datetime_parsing(self) -> None:
        raw_dt = "13-07-2023 18:00"
        parsed = parse_cwc_datetime(raw_dt)
        self.assertEqual(parsed.year, 2023)
        self.assertEqual(parsed.month, 7)
        self.assertEqual(parsed.day, 13)
        self.assertEqual(parsed.hour, 18)
        self.assertEqual(parsed.minute, 0)
        self.assertEqual(parsed.tzinfo, IST)
        self.assertEqual(parsed.isoformat(), "2023-07-13T18:00:00+05:30")

    def test_provenance_metadata_serialization(self) -> None:
        prov = ProvenanceMetadata(
            source_id="src-cwc-delhi-floods-2023",
            source_locator="CWC Case Study, Page 9",
            evidence_classification=EvidenceClassification.OBSERVED,
            retrieval_date="2026-10-11",
            transformation="Level normalized to MSL",
        )
        data = prov.to_dict()
        self.assertEqual(data["sourceId"], "src-cwc-delhi-floods-2023")
        self.assertEqual(data["evidenceClassification"], "observed")
        reconstructed = ProvenanceMetadata.from_dict(data)
        self.assertEqual(reconstructed.source_id, prov.source_id)
        self.assertEqual(reconstructed.evidence_classification, EvidenceClassification.OBSERVED)

    def test_idempotent_cwc_ingestion_and_deduplication(self) -> None:
        sample_csv_content = (
            "SlNo,Station,Agency,State LGD Code,State,District LGD Code,District,Tehsil,Block,Village,"
            "River,Basin,Tributary,Subtributary,SubSubtributary,Local River,Latitude,Longitude,"
            "Is_DischargeDataAvailable,RL_of_zeroGauge,MeanSeaLevel,Data Acquisition Time,River Water Level Manual Hourly (meter)\n"
            "1,Juddo Dam,CWC,05,Uttarakhand,063,Dehradun,Chakrata,Kalsi,Juddo,Yamuna,Yamuna Basin,Yamuna,Yamuna,Yamuna,Yamuna,30.53,77.92,No,600.0,0,01-06-2024 12:00,628.10\n"
            "2,Juddo Dam,CWC,05,Uttarakhand,063,Dehradun,Chakrata,Kalsi,Juddo,Yamuna,Yamuna Basin,Yamuna,Yamuna,Yamuna,Yamuna,30.53,77.92,No,600.0,0,01-06-2024 12:00,628.10\n"  # Duplicate
            "3,Juddo Dam,CWC,05,Uttarakhand,063,Dehradun,Chakrata,Kalsi,Juddo,Yamuna,Yamuna Basin,Yamuna,Yamuna,Yamuna,Yamuna,30.53,77.92,No,600.0,0,01-06-2024 13:00,628.35\n"
            "4,Other Station,CWC,23,MP,426,Satna,Majhgawan,Majhgawan,Rajaula,Yamuna,Yamuna Basin,Yamuna,Yamuna,Yamuna,Yamuna,25.14,80.85,No,133.0,0,01-06-2024 12:00,135.50\n"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_csv = Path(tmp_dir) / "sample.csv"
            tmp_csv.write_text(sample_csv_content, encoding="utf-8")
            out_dir = Path(tmp_dir) / "out"

            # Run 1
            report1 = ingest_cwc_hourly(tmp_csv, out_dir, station_name="Juddo Dam")
            self.assertEqual(report1["status"], "success")
            self.assertEqual(report1["validObservations"], 2)  # 3 rows, 1 duplicate discarded
            self.assertEqual(report1["duplicates"], 1)

            # Run 2 (verify idempotency)
            report2 = ingest_cwc_hourly(tmp_csv, out_dir, station_name="Juddo Dam")
            self.assertEqual(report2["validObservations"], 2)
            self.assertEqual(report2["duplicates"], 1)

            # Check output file
            out_json = Path(report1["outputPath"])
            with out_json.open("r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(len(data["observations"]), 2)
            self.assertEqual(data["observations"][0]["levelM"], 628.1)
            self.assertEqual(data["observations"][1]["levelM"], 628.35)

    def test_distinguish_zero_from_missing(self) -> None:
        sample_csv_content = (
            "SlNo,Station,Agency,State LGD Code,State,District LGD Code,District,Tehsil,Block,Village,"
            "River,Basin,Tributary,Subtributary,SubSubtributary,Local River,Latitude,Longitude,"
            "Is_DischargeDataAvailable,RL_of_zeroGauge,MeanSeaLevel,Data Acquisition Time,River Water Level Manual Hourly (meter)\n"
            "1,Juddo Dam,CWC,05,Uttarakhand,063,Dehradun,Chakrata,Kalsi,Juddo,Yamuna,Yamuna Basin,Yamuna,Yamuna,Yamuna,Yamuna,30.53,77.92,No,600.0,0,01-06-2024 12:00,\n"  # Empty missing
            "2,Juddo Dam,CWC,05,Uttarakhand,063,Dehradun,Chakrata,Kalsi,Juddo,Yamuna,Yamuna Basin,Yamuna,Yamuna,Yamuna,Yamuna,30.53,77.92,No,600.0,0,01-06-2024 13:00,0.0\n"   # Zero corrupt
            "3,Juddo Dam,CWC,05,Uttarakhand,063,Dehradun,Chakrata,Kalsi,Juddo,Yamuna,Yamuna Basin,Yamuna,Yamuna,Yamuna,Yamuna,30.53,77.92,No,600.0,0,01-06-2024 14:00,628.2\n" # Valid
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_csv = Path(tmp_dir) / "sample_missing.csv"
            tmp_csv.write_text(sample_csv_content, encoding="utf-8")
            out_dir = Path(tmp_dir) / "out"
            report = ingest_cwc_hourly(tmp_csv, out_dir, station_name="Juddo Dam")
            self.assertEqual(report["missing"], 2)
            self.assertEqual(report["validObservations"], 3)

    def test_hospital_demand_calculator_norm(self) -> None:
        calc = HospitalDemandCalculator.calculate_daily_demand(200)
        self.assertEqual(calc["bedCount"], 200)
        self.assertEqual(calc["normLitersPerBedDay"], 475.0)
        self.assertEqual(calc["recommendedDailyDemandLiters"], 95000.0)
        self.assertEqual(calc["emergency48hStorageLiters"], 190000.0)
        self.assertEqual(calc["evidenceClassification"], "derived")
        self.assertIn("IPHS", calc["sourceCitation"])
        self.assertTrue(calc["isProxy"])

    def test_july_2023_flood_scenario_replay_determinism(self) -> None:
        from ripple.models import Severity
        scen = build_historical_yamuna_2023_scenario()
        graph = DependencyGraph.from_dict(scen["graph"])
        self.assertEqual(graph.thresholds[Severity.WATCH], 204.5)

        replay_payload = {
            "schemaVersion": "1.0",
            "eventId": "flood-delhi-2023",
            "observations": scen["observations"],
        }
        res1 = run_replay(replay_payload, scen["graph"], "run-flood-1")
        res2 = run_replay(replay_payload, scen["graph"], "run-flood-1")

        self.assertEqual(res1["status"], "completed")
        self.assertEqual(res1["status"], res2["status"])
        self.assertEqual(len(res1["steps"]), len(res2["steps"]))
        self.assertEqual(len(res1["steps"]), 5)

        # Check Step 4 (207.49m critical breach)
        step4 = res1["steps"][3]
        self.assertEqual(step4["severity"], "critical")
        self.assertEqual(len(step4["impacts"]), 4)
        targets = {imp["target"]["nodeId"] for imp in step4["impacts"]}
        self.assertIn("hosp-sushruta-trauma", targets)
        self.assertIn("hosp-aruna-asaf-ali", targets)

        # Exact JSON equality across runs
        self.assertEqual(json.dumps(res1), json.dumps(res2))

    def test_data_sources_registry_coverage(self) -> None:
        chronology = get_july_2023_flood_chronology()
        self.assertEqual(len(chronology), 8)
        self.assertEqual(chronology[0]["phase"], "upstream_surge")
        self.assertEqual(chronology[6]["phase"], "peak_flood_crest")

        hospitals = get_delhi_hospitals()
        self.assertEqual(len(hospitals), 31)

        djb_records = get_djb_production_records()
        self.assertGreaterEqual(len(djb_records), 10)
        wazirabad_july = next(r for r in djb_records if r["recordDate"] == "2024-07-26" and r["wtpId"] == "wtp-wazirabad")
        self.assertEqual(wazirabad_july["shortfallMgd"], -35.0)


if __name__ == "__main__":
    unittest.main()
