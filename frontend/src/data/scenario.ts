export type Severity = 'stable' | 'watch' | 'warning' | 'critical'

export type EntityType = 'locality' | 'school' | 'college' | 'restaurant' | 'healthcare'

export type RiskZone = {
  id: string
  name: string
  plant: string
  severity: Severity
  risk: number
  supplyDrop: number
  affectedEntities: number
  path: string
  labelX: number
  labelY: number
  drivers: string[]
}

export type MapEntity = {
  id: string
  name: string
  type: EntityType
  zoneId: string
  x: number
  y: number
  demand: string
  reserve: string
  eta: string
  severity: Severity
  action: string
}

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
    activeNodes: ['gauge', 'wazirabad', 'north-zone', 'school-a'],
    confidence: 86,
  },
  {
    time: '08:20',
    elapsed: 'T+00:00',
    level: 206.12,
    severity: 'critical',
    event: 'Downstream advisory generated',
    detail: 'Locality and multi-sector entity advisories are ready for operator approval.',
    detailHi: 'Locality aur multi-sector entity advisories operator approval ke liye ready hain.',
    activeNodes: ['gauge', 'wazirabad', 'chandrawal', 'north-zone', 'central-zone', 'school-a', 'restaurant-a', 'college-a', 'locality-a'],
    confidence: 84,
  },
]

export const impacts = [
  {
    id: 'school-a',
    short: 'SC-01',
    name: 'North Delhi Public School',
    type: 'Day school · 920 people',
    eta: '38 min',
    severity: 'critical' as Severity,
    confidence: 84,
    shortageProbability: 82,
    shortageHorizon: '48 hr horizon',
    forecastFactors: ['Supply-demand gap', 'Upstream disruption', 'Low reserve'],
    forecastFeatures: { facilityId: 'school-north-01', reserveHours: 10.5, expectedSupplyM3h: 18, expectedDemandM3h: 30, riverRiseMPerHour: 0.31, upstreamDisruptionProbability: 0.84, criticality: 0.8, horizonHours: 48 },
    action: 'Verify the 10.5-hour reserve and pre-alert the school operations team.',
    actionHi: '10.5-hour reserve verify karein aur school operations team ko pre-alert bhejein.',
    path: ['Yamuna gauge', 'Wazirabad WTP', 'North supply zone', 'North Delhi Public School'],
  },
  {
    id: 'locality-a',
    short: 'L-07',
    name: 'Civil Lines Locality',
    type: 'Residential demand zone',
    eta: '1 hr 12 min',
    severity: 'warning' as Severity,
    confidence: 78,
    shortageProbability: 67,
    shortageHorizon: '48 hr horizon',
    forecastFactors: ['Low reserve', 'Supply-demand gap', 'River rise'],
    forecastFeatures: { facilityId: 'locality-civil-lines-07', reserveHours: 12, expectedSupplyM3h: 50, expectedDemandM3h: 65, riverRiseMPerHour: 0.31, upstreamDisruptionProbability: 0.78, criticality: 0.7, horizonHours: 48 },
    action: 'Notify residents and stage tankers near the affected distribution pocket.',
    actionHi: 'Residents ko notify karein aur affected distribution pocket ke paas tankers stage karein.',
    path: ['Yamuna gauge', 'Chandrawal WTP', 'Central supply zone', 'Civil Lines Locality'],
  },
  {
    id: 'restaurant-a',
    short: 'R-04',
    name: 'Kashmere Gate Kitchen',
    type: 'Restaurant · 120 seats',
    eta: '2 hr 05 min',
    severity: 'watch' as Severity,
    confidence: 72,
    shortageProbability: 41,
    shortageHorizon: '72 hr horizon',
    forecastFactors: ['River rise', 'Upstream disruption', 'Demand increase'],
    forecastFeatures: { facilityId: 'restaurant-kashmere-gate-04', reserveHours: 6.2, expectedSupplyM3h: 4.6, expectedDemandM3h: 6.8, riverRiseMPerHour: 0.31, upstreamDisruptionProbability: 0.7, criticality: 0.45, horizonHours: 72 },
    action: 'Protect potable inventory and schedule a 5 KL replenishment window.',
    actionHi: 'Potable inventory protect karein aur 5 KL replenishment window schedule karein.',
    path: ['Yamuna gauge', 'Wazirabad WTP', 'North supply zone', 'Kashmere Gate Kitchen'],
  },
  {
    id: 'college-a',
    short: 'C-03',
    name: 'North Campus College',
    type: 'College · day campus',
    eta: '2 hr 34 min',
    severity: 'watch' as Severity,
    confidence: 70,
    shortageProbability: 37,
    shortageHorizon: '72 hr horizon',
    forecastFactors: ['Campus demand', 'Supply-demand gap', 'River rise'],
    forecastFeatures: { facilityId: 'college-north-campus-03', reserveHours: 28, expectedSupplyM3h: 29, expectedDemandM3h: 34, riverRiseMPerHour: 0.31, upstreamDisruptionProbability: 0.64, criticality: 0.5, horizonHours: 72 },
    action: 'Verify campus tanks and pause non-essential landscape use.',
    actionHi: 'Campus tanks verify karein aur non-essential landscape use pause karein.',
    path: ['Yamuna gauge', 'Wazirabad WTP', 'North supply zone', 'North Campus College'],
  },
]

export const riskZones: RiskZone[] = [
  {
    id: 'north', name: 'North Delhi', plant: 'Wazirabad WTP', severity: 'critical', risk: 84,
    supplyDrop: 38, affectedEntities: 18,
    path: 'M222 64 L361 42 L453 92 L441 178 L374 224 L259 205 L194 142 Z',
    labelX: 325, labelY: 128,
    drivers: ['WTP capacity loss', 'Fast river rise', 'Complaint acceleration'],
  },
  {
    id: 'west', name: 'West Delhi', plant: 'Haiderpur WTP', severity: 'stable', risk: 22,
    supplyDrop: 6, affectedEntities: 4,
    path: 'M103 189 L194 142 L259 205 L271 316 L196 391 L95 336 L70 252 Z',
    labelX: 168, labelY: 278,
    drivers: ['Normal production', 'Stable reserve', 'Low complaint volume'],
  },
  {
    id: 'central', name: 'Central Delhi', plant: 'Chandrawal WTP', severity: 'warning', risk: 67,
    supplyDrop: 24, affectedEntities: 11,
    path: 'M259 205 L374 224 L427 300 L374 376 L271 316 Z',
    labelX: 343, labelY: 287,
    drivers: ['Chandrawal watch', 'Low-pressure reports', 'Peak demand window'],
  },
  {
    id: 'east', name: 'East Delhi', plant: 'Bhagirathi WTP', severity: 'watch', risk: 43,
    supplyDrop: 12, affectedEntities: 7,
    path: 'M441 178 L508 220 L536 329 L475 408 L374 376 L427 300 L374 224 Z',
    labelX: 457, labelY: 293,
    drivers: ['Distribution lag', 'Moderate demand', 'Reserve available'],
  },
  {
    id: 'south', name: 'South Delhi', plant: 'Okhla WTP', severity: 'warning', risk: 58,
    supplyDrop: 19, affectedEntities: 9,
    path: 'M196 391 L271 316 L374 376 L475 408 L443 531 L350 590 L247 540 L169 461 Z',
    labelX: 332, labelY: 463,
    drivers: ['Okhla supply watch', 'High commercial demand', 'Uneven reserves'],
  },
]

export const mapEntities: MapEntity[] = [
  { id: 'map-school-north', name: 'North Delhi Public School', type: 'school', zoneId: 'north', x: 307, y: 112, demand: '41.4 KL/day', reserve: '10.5 hr', eta: '38 min', severity: 'critical', action: 'Verify storage and alert operations.' },
  { id: 'map-college-north', name: 'North Campus College', type: 'college', zoneId: 'north', x: 365, y: 164, demand: '126 KL/day', reserve: '28 hr', eta: '2 hr 34 min', severity: 'watch', action: 'Pause non-essential campus use.' },
  { id: 'map-health-central', name: 'Civil Lines Clinic', type: 'healthcare', zoneId: 'central', x: 356, y: 257, demand: '31 KL/day', reserve: '12 hr', eta: '1 hr 12 min', severity: 'warning', action: 'Protect clinical reserve and verify tank level.' },
  { id: 'map-locality-central', name: 'Civil Lines Locality', type: 'locality', zoneId: 'central', x: 309, y: 319, demand: '2.1 ML/day', reserve: 'Mixed', eta: '1 hr 12 min', severity: 'warning', action: 'Notify residents and stage tankers.' },
  { id: 'map-restaurant-east', name: 'Kashmere Gate Kitchen', type: 'restaurant', zoneId: 'east', x: 458, y: 273, demand: '8.4 KL/day', reserve: '6.2 hr', eta: '2 hr 05 min', severity: 'watch', action: 'Schedule a 5 KL replenishment window.' },
  { id: 'map-school-west', name: 'West Delhi Senior School', type: 'school', zoneId: 'west', x: 178, y: 270, demand: '52 KL/day', reserve: '31 hr', eta: 'No impact', severity: 'stable', action: 'Continue normal monitoring.' },
  { id: 'map-restaurant-south', name: 'South Market Food Court', type: 'restaurant', zoneId: 'south', x: 376, y: 446, demand: '19 KL/day', reserve: '8.5 hr', eta: '3 hr 10 min', severity: 'warning', action: 'Reduce cleaning-cycle demand and verify reserve.' },
  { id: 'map-locality-east', name: 'Shahdara Pocket', type: 'locality', zoneId: 'east', x: 480, y: 345, demand: '1.6 ML/day', reserve: 'Mixed', eta: '4 hr 20 min', severity: 'watch', action: 'Monitor complaint acceleration.' },
]

export const levelPoints = [204.1, 204.35, 204.7, 205.0, 205.35, 205.78, 206.12]
