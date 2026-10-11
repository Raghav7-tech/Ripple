export type ApiHealth = {
  status: 'ok'
  version: string
  time: string
  mode: string
}

export type ShortageFeatures = {
  facilityId: string
  reserveHours: number
  expectedSupplyM3h: number
  expectedDemandM3h: number
  riverRiseMPerHour: number
  upstreamDisruptionProbability: number
  criticality: number
  horizonHours: number
}

export type ShortageForecast = {
  schemaVersion: '1.0'
  facilityId: string
  shortageProbability: number
  estimatedHoursToShortage: number | null
  riskBand: 'low' | 'moderate' | 'high' | 'critical'
  horizonHours: number
  topFactors: string[]
  modelVersion: string
  productionReady: boolean
}

export type ResourceLane = 'water' | 'staff' | 'medical_supply'

export type EvidenceClassification = 'observed' | 'reported_event' | 'derived' | 'assumed' | 'synthetic'

export type GraphNode = {
  nodeId: string
  name: string
  type: string
  notify: boolean
  severityCap: 'stable' | 'watch' | 'warning' | 'critical'
  evidenceStatus: 'verified' | 'inferred' | 'demonstration'
  assumption?: string | null
  sourceId?: string
  sourceLocator?: string
  evidenceClassification?: EvidenceClassification
  bedCount?: number
  capacityMgd?: number
  operationalStatus?: string
}

export type GraphEdge = {
  edgeId: string
  from: string
  to: string
  delayMinutes: number
  confidence: number
  minSeverity: 'stable' | 'watch' | 'warning' | 'critical'
  evidenceStatus: 'verified' | 'inferred' | 'demonstration'
  assumption?: string | null
  resourceType?: ResourceLane
  sourceId?: string
  sourceLocator?: string
  evidenceClassification?: EvidenceClassification
}

export type DependencyGraph = {
  schemaVersion: '1.0'
  graphVersion: string
  createdAt: string
  approvedAt: string | null
  thresholdsM: {
    watch: number
    warning: number
    critical: number
  }
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export type Observation = {
  schemaVersion: '1.0'
  observationId: string
  eventId: string
  sourceNodeId: string
  observedAt: string
  receivedAt: string
  levelM: number
  confidence: number
  mode: string
  sourceId: string
}

export type PathStep = {
  edgeId: string
  from: string
  to: string
  delayMinutes: number
  confidence: number
  evidenceStatus: string
  assumption?: string | null
  resourceType: ResourceLane
}

export type SimulationImpact = {
  schemaVersion: '1.0'
  impactId: string
  runId: string
  target: {
    nodeId: string
    name: string
  }
  expectedImpactAt: string
  etaMinutes: number
  severity: 'stable' | 'watch' | 'warning' | 'critical'
  confidence: number
  resourceType: ResourceLane
  path: PathStep[]
}

export type SimulationRequest = {
  runId?: string
  graph: DependencyGraph
  observation: Observation
}

export type SimulationResponse = {
  schemaVersion: '1.0'
  runId: string
  observationId: string
  severity: 'stable' | 'watch' | 'warning' | 'critical'
  impacts: SimulationImpact[]
  correlationId: string
  engineCalculationMs: number
}

const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '')

export const apiConfigured = Boolean(apiBase)
export const configuredApiBase = apiBase || ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (!apiBase) throw new Error('VITE_API_BASE_URL is not configured')
  let response: Response
  try {
    response = await fetch(`${apiBase}${path}`, {
      ...init,
      headers: { 'content-type': 'application/json', ...init?.headers },
    })
  } catch (err) {
    if (init?.signal?.aborted) throw new DOMException('Aborted', 'AbortError')
    throw new Error(`Network error connecting to Ripple API (${apiBase}): ${err instanceof Error ? err.message : String(err)}`)
  }

  if (!response.ok) {
    let errorDetail = `Ripple API returned ${response.status} ${response.statusText}`
    try {
      const errJson = await response.json()
      if (errJson?.error?.message) {
        errorDetail = errJson.error.code ? `[${errJson.error.code}] ${errJson.error.message}` : errJson.error.message
      } else if (errJson?.message) {
        errorDetail = errJson.message
      }
    } catch {
      // response body was not JSON
    }
    throw new Error(errorDetail)
  }

  return response.json() as Promise<T>
}

export function getHealth(signal?: AbortSignal) {
  return request<ApiHealth>('/health', { signal })
}

export function predictShortage(features: ShortageFeatures, signal?: AbortSignal) {
  return request<ShortageForecast>('/forecasts/shortage', {
    method: 'POST',
    body: JSON.stringify({ features }),
    signal,
  })
}

export async function runCascadeSimulation(
  payload: SimulationRequest,
  signal?: AbortSignal,
): Promise<SimulationResponse> {
  const result = await request<SimulationResponse>('/modeling/simulate', {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  })

  if (
    !result ||
    result.schemaVersion !== '1.0' ||
    typeof result.runId !== 'string' ||
    typeof result.severity !== 'string' ||
    !Array.isArray(result.impacts) ||
    typeof result.engineCalculationMs !== 'number'
  ) {
    throw new Error('Simulation endpoint returned an invalid response structure')
  }

  return result
}
