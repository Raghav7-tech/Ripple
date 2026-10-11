import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repoRoot = path.resolve(import.meta.dirname, "../..");
const csvPath = path.join(repoRoot, "data/training/synthetic_shortage_v1.csv");
const metadataPath = path.join(repoRoot, "data/training/synthetic_shortage_v1.metadata.json");
const anchorsPath = path.join(repoRoot, "data/training/verified_event_anchors.jsonl");
const outputPath = path.join(repoRoot, "data/training/Ripple_Dataset_Review_v0.xlsx");
const previewDir = path.join(repoRoot, ".tmp/dataset-workbook-preview");

const csvText = await fs.readFile(csvPath, "utf8");
const imported = await Workbook.fromCSV(csvText, { sheetName: "Synthetic rows" });
const importedSheet = imported.worksheets.getItem("Synthetic rows");
const importedValues = importedSheet.getUsedRange(true).values;
const headers = importedValues[0].map(String);
const numericColumns = new Set([
  "river_level_m", "river_rise_m_per_hour", "rainfall_mm_24h", "max_temperature_c",
  "treatment_capacity_pct", "expected_supply_m3h", "expected_demand_m3h", "reserve_hours",
  "upstream_disruption_probability", "criticality", "sensor_quality", "horizon_hours",
  "hours_to_shortage",
]);
const booleanColumns = new Set(["outage_active", "shortage_within_horizon", "synthetic"]);
const typedRows = importedValues.slice(1).map((row) => row.map((value, index) => {
  const header = headers[index];
  if (numericColumns.has(header)) return value === "" ? null : Number(value);
  if (booleanColumns.has(header)) return String(value).toLowerCase() === "true";
  if (header === "timestamp") return new Date(String(value));
  return value;
}));

const metadata = JSON.parse(await fs.readFile(metadataPath, "utf8"));
const anchors = (await fs.readFile(anchorsPath, "utf8"))
  .trim()
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => JSON.parse(line));

const workbook = Workbook.create();
const summary = workbook.worksheets.add("Summary");
const dictionary = workbook.worksheets.add("Data dictionary");
const events = workbook.worksheets.add("Verified anchors");
const data = workbook.worksheets.add("Synthetic rows");
for (const sheet of [summary, dictionary, events, data]) sheet.showGridLines = false;

const navy = "#0B2631";
const teal = "#0F766E";
const mint = "#CFF8E8";
const pale = "#EAF4F1";
const amber = "#FFF1CC";
const coral = "#FCE2DE";
const line = "#CAD8D5";
const text = "#14262C";
const muted = "#52676D";
const font = "Arial";

summary.getRange("A2:H2").merge();
summary.getRange("A2").values = [["Ripple shortage dataset review"]];
summary.getRange("A2:H2").format = { font: { name: font, size: 16, bold: true, color: text } };
summary.getRange("A3:H3").format.borders = { bottom: { style: "thin", color: teal } };
summary.getRange("A5:B11").values = [
  ["Dataset ID", metadata.datasetId],
  ["Synthetic rows", null],
  ["Positive shortage labels", metadata.positiveCount],
  ["Positive rate", null],
  ["Event groups", metadata.eventCount],
  ["Verified event anchors", anchors.length],
  ["Operational use", "Not allowed"],
];
const lastDataRow = typedRows.length + 1;
summary.getRange("B6").formulas = [[`=COUNTA('Synthetic rows'!A2:A${lastDataRow})`]];
summary.getRange("B8").formulas = [["=B7/B6"]];
summary.getRange("A5:A11").format = { fill: pale, font: { name: font, bold: true, color: text } };
summary.getRange("B5:B11").format = { font: { name: font, color: text } };
summary.getRange("B8").format.numberFormat = "0.0%";
summary.getRange("D5:H5").merge();
summary.getRange("D5").values = [["Current limitation"]];
summary.getRange("D5:H5").format = { fill: amber, font: { name: font, bold: true, color: text } };
summary.getRange("D6:H9").merge();
summary.getRange("D6").values = [["Official sources verify historical hazard and plant outcomes, but do not provide facility-level reserve depletion timestamps. The synthetic rows are suitable for pipeline development only. Retrain and calibrate on reviewed utility or facility labels before operational use."]];
summary.getRange("D6:H9").format = { fill: "#FFF9EA", font: { name: font, color: text }, wrapText: true, verticalAlignment: "top" };
summary.getRange("A13:H13").merge();
summary.getRange("A13").values = [["Recommended next data collection"]];
summary.getRange("A13:H13").format = { fill: navy, font: { name: font, bold: true, color: "#FFFFFF" } };
summary.getRange("A14:H19").values = [
  ["Priority", "Dataset", "Required fields", "Owner", "Evidence", "Status", "", ""],
  ["1", "Facility telemetry", "Hourly reserve volume, inflow and demand", "Facility operator", "Verified", "Required", "", ""],
  ["2", "Treatment operations", "Plant production, outage start/end and restoration", "Utility", "Verified", "Required", "", ""],
  ["3", "Distribution", "Zone flow and pressure", "Utility", "Verified", "Required", "", ""],
  ["4", "Hazard", "River level, rainfall and rate of rise", "CWC / IMD", "Verified", "Available", "", ""],
  ["5", "Outcome label", "Timestamp reserve crossed reviewed minimum", "Facility operator", "Verified", "Missing", "", ""],
];
summary.getRange("A14:F19").format = { font: { name: font, color: text }, borders: { preset: "inside", style: "thin", color: line } };
summary.getRange("A14:F14").format = { fill: pale, font: { name: font, bold: true, color: text }, wrapText: true };

const dictionaryRows = [
  ["Column", "Type", "Unit", "Role", "Description"],
  ["event_id", "text", "", "split key", "Groups every observation from one disruption event."],
  ["timestamp", "datetime", "ISO 8601", "feature time", "Time at which all features must be known."],
  ["entity_type", "category", "", "segment", "Locality, school, college, restaurant or healthcare."],
  ["river_level_m", "number", "m", "feature", "Observed or simulated river level."],
  ["river_rise_m_per_hour", "number", "m/hour", "feature", "Recent rate of level change."],
  ["treatment_capacity_pct", "number", "%", "feature", "Available treatment capacity at feature time."],
  ["expected_supply_m3h", "number", "m³/hour", "feature", "Expected supply delivered to the entity or zone."],
  ["expected_demand_m3h", "number", "m³/hour", "feature", "Expected entity demand."],
  ["reserve_hours", "number", "hours", "feature", "Usable reserve at current demand."],
  ["upstream_disruption_probability", "number", "0–1", "feature", "Probability supplied by the deterministic cascade."],
  ["criticality", "number", "0–1", "feature", "Reviewed service criticality band encoded numerically."],
  ["horizon_hours", "integer", "hours", "prediction horizon", "Time window for the classification label."],
  ["shortage_within_horizon", "boolean", "", "target", "Whether usable reserve crossed its reviewed minimum in the horizon."],
  ["hours_to_shortage", "number/null", "hours", "secondary target", "Time from feature timestamp to verified threshold crossing."],
  ["evidence_status", "category", "", "governance", "Verified, inferred or demonstration."],
  ["synthetic", "boolean", "", "governance", "True for generated records."],
  ["source_ids", "text", "", "provenance", "IDs from the source register."],
];
dictionary.getRange(`A1:E${dictionaryRows.length}`).values = dictionaryRows;

const eventRows = [["Event ID", "Date", "Hazard", "Verified outcome", "Entity shortage timestamp", "Evidence", "Source IDs"]];
for (const event of anchors) {
  const signals = event.verifiedSignals;
  eventRows.push([
    event.eventId,
    new Date(`${event.eventDate}T00:00:00Z`),
    event.hazard,
    JSON.stringify(signals),
    event.facilityShortageTimestamp ?? "Not available",
    event.evidenceStatus,
    event.sourceIds.join(", "),
  ]);
}
events.getRange(`A1:G${eventRows.length}`).values = eventRows;

data.getRangeByIndexes(0, 0, typedRows.length + 1, headers.length).values = [headers, ...typedRows];

for (const sheet of [dictionary, events, data]) {
  const used = sheet.getUsedRange();
  used.format.font = { name: font, size: 10, color: text };
  used.format.verticalAlignment = "center";
  const header = used.getRow(0);
  header.format = { fill: navy, font: { name: font, size: 10, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
  header.format.borders = { preset: "inside", style: "thin", color: "#FFFFFF" };
  sheet.freezePanes.freezeRows(1);
}

dictionary.getRange("A2:A18").format.font = { name: font, bold: true, color: teal };
dictionary.getRange("A1:E18").format.autofitColumns();
dictionary.getRange("D:E").format.wrapText = true;
dictionary.getRange("A:A").format.columnWidth = 34;
dictionary.getRange("E:E").format.columnWidth = 55;

events.getRange("B2:B4").format.numberFormat = "yyyy-mm-dd";
events.getRange("A1:G4").format.autofitColumns();
events.getRange("D:D").format.columnWidth = 65;
events.getRange("D:G").format.wrapText = true;

data.freezePanes.freezeColumns(4);
data.getRange(`E2:E${lastDataRow}`).format.numberFormat = "yyyy-mm-dd hh:mm";
for (const col of ["I", "J", "K", "L", "M", "N", "O", "P", "Q", "S", "T", "U", "W"] ) {
  data.getRange(`${col}2:${col}${lastDataRow}`).format.numberFormat = "0.000";
}
data.getRange(`V2:V${lastDataRow}`).conditionalFormats.add("expression", { formula: "=$V2=TRUE", format: { fill: coral, font: { bold: true, color: "#9E2A1F" } } });
data.getRange(`A1:AA${lastDataRow}`).format.autofitColumns();
for (const col of ["A", "B", "C", "D", "F", "G", "H", "X", "Y", "Z", "AA"]) data.getRange(`${col}:${col}`).format.columnWidth = 20;

summary.getRange("A1:H19").format.font = { name: font, size: 10, color: text };
summary.getRange("A1:H19").format.verticalAlignment = "center";
summary.getRange("A:A").format.columnWidth = 12;
summary.getRange("B:B").format.columnWidth = 25;
summary.getRange("C:C").format.columnWidth = 3;
for (const col of ["D", "E", "F", "G", "H"]) summary.getRange(`${col}:${col}`).format.columnWidth = 18;
summary.getRange("C14:C19").format.columnWidth = 45;
summary.getRange("A2:H19").format.rowHeight = 22;
summary.getRange("D6:H9").format.rowHeight = 32;
// Re-apply the section header after the sheet-wide font defaults above.
summary.getRange("A13:H13").format = { fill: navy, font: { name: font, bold: true, color: "#FFFFFF" } };
summary.tabColor = navy;
dictionary.tabColor = teal;
events.tabColor = "#5A8891";

workbook.recalculate();
const summaryCheck = await workbook.inspect({ kind: "table", range: "Summary!A2:H19", include: "values,formulas", tableMaxRows: 20, tableMaxCols: 8 });
console.log(summaryCheck.ndjson);
const errorCheck = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 100 }, summary: "final formula error scan" });
console.log(errorCheck.ndjson);

await fs.mkdir(previewDir, { recursive: true });
for (const sheetName of ["Summary", "Data dictionary", "Verified anchors", "Synthetic rows"]) {
  const preview = await workbook.render({
    sheetName,
    range: sheetName === "Synthetic rows" ? "A1:AA45" : undefined,
    autoCrop: "all",
    scale: sheetName === "Synthetic rows" ? 0.6 : 1,
    format: "png",
  });
  await fs.writeFile(path.join(previewDir, `${sheetName.replaceAll(" ", "-")}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
