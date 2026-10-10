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

const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '')

export const apiConfigured = Boolean(apiBase)

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (!apiBase) throw new Error('VITE_API_BASE_URL is not configured')
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: { 'content-type': 'application/json', ...init?.headers },
  })
  if (!response.ok) throw new Error(`Ripple API returned ${response.status}`)
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
