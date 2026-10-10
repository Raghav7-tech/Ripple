export type Severity = 'stable' | 'watch' | 'warning' | 'critical'

export type ScenarioStep = {
  time: string
  elapsed: string
  level: number
  severity: Severity
  event: string
  detail: string
  detailHi: string
  activeNodes: string[]
  confidence: number
}

export const scenarioSteps: ScenarioStep[] = [
  {
    time: '05:00',
    elapsed: 'T−03:20',
    level: 204.1,
    severity: 'stable',
    event: 'Baseline observation received',
    detail: 'River level is below the warning threshold. Dependency graph is ready.',
    detailHi: 'River level warning threshold se neeche hai. Dependency graph ready hai.',
    activeNodes: ['gauge'],
    confidence: 98,
  },
  {
    time: '06:10',
    elapsed: 'T−02:10',
    level: 204.7,
    severity: 'watch',
    event: 'Rate-of-rise watch started',
    detail: 'The six-hour rise is accelerating. Treatment assets enter watch mode.',
    detailHi: '6-hour rise tez ho rahi hai. Treatment assets watch mode mein aa gaye hain.',
    activeNodes: ['gauge', 'wazirabad', 'chandrawal'],
    confidence: 92,
  },
  {
    time: '07:05',
    elapsed: 'T−01:15',
    level: 205.35,
    severity: 'warning',
    event: 'Warning threshold crossed',
    detail: 'Low-lying intake infrastructure may become inaccessible within 75 minutes.',
    detailHi: 'Low-lying intake infrastructure 75 minutes mein inaccessible ho sakta hai.',
    activeNodes: ['gauge', 'wazirabad', 'chandrawal', 'north-zone'],
    confidence: 88,
  },
  {
    time: '07:42',
    elapsed: 'T−00:38',
    level: 205.78,
    severity: 'warning',
    event: 'Capacity-loss path detected',
    detail: 'A likely Wazirabad capacity reduction propagates to North Delhi supply zones.',
    detailHi: 'Wazirabad ki likely capacity reduction North Delhi supply zones tak propagate hogi.',
    activeNodes: ['gauge', 'wazirabad', 'north-zone', 'hospital-a'],
    confidence: 86,
  },
  {
    time: '08:20',
    elapsed: 'T+00:00',
    level: 206.12,
    severity: 'critical',
    event: 'Downstream advisory generated',
    detail: 'Hospital and public-service advisories are ready for operator approval.',
    detailHi: 'Hospital aur public-service advisories operator approval ke liye ready hain.',
    activeNodes: ['gauge', 'wazirabad', 'chandrawal', 'north-zone', 'central-zone', 'hospital-a', 'hospital-b'],
    confidence: 84,
  },
]

export const impacts = [
  {
    id: 'hospital-a',
    short: 'H-01',
    name: 'North District Hospital',
    type: 'Critical care facility',
    eta: '38 min',
    severity: 'critical' as Severity,
    confidence: 84,
    shortageProbability: 82,
    shortageHorizon: '48 hr horizon',
    forecastFactors: ['Supply-demand gap', 'Upstream disruption', 'Low reserve'],
    forecastFeatures: { facilityId: 'hospital-north-01', reserveHours: 18, expectedSupplyM3h: 42, expectedDemandM3h: 70, riverRiseMPerHour: 0.31, upstreamDisruptionProbability: 0.84, criticality: 1, horizonHours: 48 },
    action: 'Confirm 18-hour reserve and pre-alert tanker vendor.',
    actionHi: '18-hour reserve confirm karein aur tanker vendor ko pre-alert bhejein.',
    path: ['Yamuna gauge', 'Wazirabad WTP', 'North supply zone', 'North District Hospital'],
  },
  {
    id: 'hospital-b',
    short: 'H-02',
    name: 'Civil Lines Clinic',
    type: 'Community health facility',
    eta: '1 hr 12 min',
    severity: 'warning' as Severity,
    confidence: 78,
    shortageProbability: 67,
    shortageHorizon: '48 hr horizon',
    forecastFactors: ['Low reserve', 'Supply-demand gap', 'River rise'],
    forecastFeatures: { facilityId: 'clinic-civil-lines-01', reserveHours: 12, expectedSupplyM3h: 50, expectedDemandM3h: 65, riverRiseMPerHour: 0.31, upstreamDisruptionProbability: 0.78, criticality: 0.8, horizonHours: 48 },
    action: 'Reduce non-essential consumption and verify storage level.',
    actionHi: 'Non-essential consumption kam karein aur storage level verify karein.',
    path: ['Yamuna gauge', 'Chandrawal WTP', 'Central supply zone', 'Civil Lines Clinic'],
  },
  {
    id: 'shelter-a',
    short: 'S-04',
    name: 'Kashmere Gate Shelter',
    type: 'Emergency shelter',
    eta: '2 hr 05 min',
    severity: 'watch' as Severity,
    confidence: 72,
    shortageProbability: 41,
    shortageHorizon: '72 hr horizon',
    forecastFactors: ['River rise', 'Upstream disruption', 'Demand increase'],
    forecastFeatures: { facilityId: 'shelter-kashmere-gate-04', reserveHours: 36, expectedSupplyM3h: 50, expectedDemandM3h: 60, riverRiseMPerHour: 0.31, upstreamDisruptionProbability: 0.7, criticality: 0.5, horizonHours: 72 },
    action: 'Inspect potable-water inventory before intake increases.',
    actionHi: 'Intake badhne se pehle potable-water inventory inspect karein.',
    path: ['Yamuna gauge', 'Wazirabad WTP', 'North supply zone', 'Kashmere Gate Shelter'],
  },
]

export const levelPoints = [204.1, 204.35, 204.7, 205.0, 205.35, 205.78, 206.12]
