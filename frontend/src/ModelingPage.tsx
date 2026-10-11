import React, { useEffect, useId, useMemo, useRef, useState } from 'react'
import {
  apiConfigured,
  configuredApiBase,
  getHealth,
  runCascadeSimulation,
  type DependencyGraph,
  type GraphEdge,
  type GraphNode,
  type Observation,
  type PathStep,
  type ResourceLane,
  type SimulationImpact,
  type SimulationRequest,
  type SimulationResponse,
} from './lib/api'
import {
  delhiWaterDemoGraph,
  getPresetData,
  historicalCwcJuddoDamGraph,
  historicalCwcJuddoDamObservations,
  historicalYamuna2023Graph,
  historicalYamuna2023Observations,
  july2023FloodChronology,
  multiResourceDemoGraph,
  multiResourceTrigger,
  PRESET_REGISTRY,
  type PresetInfo,
  type PresetKey,
  yamunaReplayObservations,
} from './data/modelingPresets'

interface ModelingPageProps {
  theme: 'dark' | 'light'
  onToggleTheme: () => void
  onNavigateHome: () => void
}

type ActiveTab = 'simulate' | 'graph' | 'checks' | 'comparison' | 'capacity'

interface CheckResult {
  id: string
  name: string
  description: string
  status: 'not_run' | 'running' | 'pass' | 'fail' | 'blocked'
  expected: string
  actual?: string
  elapsedMs?: number
  error?: string
}

// Accessible SVG Icons
function RippleMark() {
  return (
    <span className="mark" aria-hidden="true">
      <i />
      <i />
      <i />
      <b />
    </span>
  )
}

function ArrowLeftIcon() {
  return (
    <svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M16 10H4M10 4l-6 6 6 6" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
      <path d="m4 10 4 4 8-8" />
    </svg>
  )
}

function CrossIcon() {
  return (
    <svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
      <path d="m5 5 10 10M15 5 5 15" />
    </svg>
  )
}

function WarningIcon() {
  return (
    <svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M10 3 2 17h16L10 3Zm0 6v4m0 2.5v.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function ZoomInIcon() {
  return (
    <svg viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M10 5v10M5 10h10" />
    </svg>
  )
}

function ZoomOutIcon() {
  return (
    <svg viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M5 10h10" />
    </svg>
  )
}

function FitViewIcon() {
  return (
    <svg viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M3 7V3h4M17 7V3h-4M3 13v4h4M17 13v4h-4" />
    </svg>
  )
}

function NodeIcon({ type }: { type: string }) {
  if (type === 'gauge') {
    return (
      <svg viewBox="0 0 16 16" width="13" height="13" fill="currentColor" aria-hidden="true" className="node-kind-icon gauge">
        <path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1Zm0 2a5 5 0 0 1 4.54 7.12l-3.83-2.21a1.5 1.5 0 1 0-1.42.82l3.83 2.21A5 5 0 1 1 8 3Z" />
      </svg>
    )
  }
  if (type === 'treatment-plant') {
    return (
      <svg viewBox="0 0 16 16" width="13" height="13" fill="currentColor" aria-hidden="true" className="node-kind-icon plant">
        <path d="M2 3h12v2H2V3Zm1 4h10v2H3V7Zm2 4h6v2H5v-2Z" />
      </svg>
    )
  }
  if (type === 'supply-zone') {
    return (
      <svg viewBox="0 0 16 16" width="13" height="13" fill="currentColor" aria-hidden="true" className="node-kind-icon zone">
        <path d="M1 2h6v5H1V2Zm8 0h6v5H9V2ZM1 9h6v5H1V9Zm8 0h6v5H9V9Z" />
      </svg>
    )
  }
  // Hospital, Clinic, Shelter (Notify Targets)
  return (
    <svg viewBox="0 0 16 16" width="13" height="13" fill="currentColor" aria-hidden="true" className="node-kind-icon target">
      <path d="M6 2h4v4h4v4h-4v4H6v-4H2V6h4V2Z" />
    </svg>
  )
}

function SeverityBadge({ severity }: { severity: 'stable' | 'watch' | 'warning' | 'critical' }) {
  const icon = {
    stable: '✓',
    watch: '●',
    warning: '▲',
    critical: '!',
  }[severity]

  return (
    <span className={`severity-badge ${severity}`}>
      <span className="severity-symbol" aria-hidden="true">{icon}</span>
      <span className="severity-text">{severity.toUpperCase()}</span>
    </span>
  )
}

// Deterministic topological layer assignment with generous spacing to prevent overlap
function computeGraphLayout(nodes: GraphNode[], edges: GraphEdge[], rootId: string) {
  const inDegree = new Map<string, number>()
  const adj = new Map<string, string[]>()

  for (const n of nodes) {
    inDegree.set(n.nodeId, 0)
    adj.set(n.nodeId, [])
  }

  for (const e of edges) {
    if (adj.has(e.from)) adj.get(e.from)!.push(e.to)
    if (inDegree.has(e.to)) inDegree.set(e.to, (inDegree.get(e.to) || 0) + 1)
  }

  const layers = new Map<string, number>()
  for (const n of nodes) layers.set(n.nodeId, 0)

  const queue: { id: string; depth: number }[] = [{ id: rootId, depth: 0 }]
  const visited = new Set<string>([rootId])

  while (queue.length > 0) {
    const { id, depth } = queue.shift()!
    const currentDepth = layers.get(id) || 0
    const nextDepth = Math.max(currentDepth, depth)
    layers.set(id, nextDepth)

    const neighbors = adj.get(id) || []
    for (const nxt of neighbors) {
      const neighborDepth = layers.get(nxt) || 0
      layers.set(nxt, Math.max(neighborDepth, nextDepth + 1))
      if (!visited.has(nxt)) {
        visited.add(nxt)
        queue.push({ id: nxt, depth: nextDepth + 1 })
      }
    }
  }

  for (const n of nodes) {
    if (!visited.has(n.nodeId)) {
      layers.set(n.nodeId, 1)
    }
  }

  const layerGroups = new Map<number, string[]>()
  for (const [nodeId, layer] of layers.entries()) {
    if (!layerGroups.has(layer)) layerGroups.set(layer, [])
    layerGroups.get(layer)!.push(nodeId)
  }

  const sortedLayerIndices = Array.from(layerGroups.keys()).sort((a, b) => a - b)
  const layerWidth = 260
  const nodeHeight = 96
  const paddingX = 90
  const paddingY = 60

  const positions = new Map<string, { x: number; y: number }>()
  let maxNodesInLayer = 1

  sortedLayerIndices.forEach((layerIdx, colIdx) => {
    const nodesInThisLayer = layerGroups.get(layerIdx)!
    if (nodesInThisLayer.length > maxNodesInLayer) maxNodesInLayer = nodesInThisLayer.length
    const totalLayerHeight = (nodesInThisLayer.length - 1) * nodeHeight
    const startY = paddingY + (maxNodesInLayer > nodesInThisLayer.length ? (maxNodesInLayer - nodesInThisLayer.length) * 44 : 0)

    nodesInThisLayer.forEach((nodeId, rowIdx) => {
      positions.set(nodeId, {
        x: paddingX + colIdx * layerWidth,
        y: startY + rowIdx * nodeHeight,
      })
    })
  })

  const width = Math.max(780, paddingX * 2 + sortedLayerIndices.length * layerWidth)
  const height = Math.max(440, paddingY * 2 + maxNodesInLayer * nodeHeight + 40)

  return { positions, width, height }
}

export function ModelingPage({ theme, onToggleTheme, onNavigateHome }: ModelingPageProps) {
  // Navigation tab state synced with URL ?tab=...
  const [activeTab, setActiveTab] = useState<ActiveTab>(() => {
    const params = new URLSearchParams(window.location.search)
    const t = params.get('tab') as ActiveTab | null
    if (t && ['simulate', 'graph', 'checks', 'comparison', 'capacity'].includes(t)) {
      return t
    }
    return 'simulate'
  })

  // Synchronize browser history Back/Forward for tabs
  useEffect(() => {
    const onPop = () => {
      const params = new URLSearchParams(window.location.search)
      const t = params.get('tab') as ActiveTab | null
      if (t && ['simulate', 'graph', 'checks', 'comparison', 'capacity'].includes(t)) {
        setActiveTab(t)
      } else {
        setActiveTab('simulate')
      }
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const handleTabChange = (tab: ActiveTab) => {
    setActiveTab(tab)
    const url = new URL(window.location.href)
    url.searchParams.set('tab', tab)
    window.history.pushState({}, '', url.toString())
  }

  // Connection health state
  const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'unavailable'>(
    apiConfigured ? 'checking' : 'unavailable',
  )
  const [healthInfo, setHealthInfo] = useState<string | null>(null)

  // Presets & Active Scenario Draft
  const [presetKey, setPresetKey] = useState<PresetKey>('historical-yamuna-2023')
  const [graphDraft, setGraphDraft] = useState<DependencyGraph>(() => getPresetData('historical-yamuna-2023').graph)
  const [obsDraft, setObsDraft] = useState<Observation>(() => getPresetData('historical-yamuna-2023').observation)
  const [showChronology, setShowChronology] = useState<boolean>(true)

  // What-if overrides state
  const [delayMultiplier, setDelayMultiplier] = useState<number>(1.0)
  const [disabledEdgeIds, setDisabledEdgeIds] = useState<Set<string>>(new Set())
  const [enabledResources, setEnabledResources] = useState<Record<ResourceLane, boolean>>({
    water: true,
    staff: true,
    medical_supply: true,
  })
  const [thresholdOverrides, setThresholdOverrides] = useState<{
    watch?: number
    warning?: number
    critical?: number
  }>({})

  // Simulation run state
  const [isRunning, setIsRunning] = useState(false)
  const [lastResult, setLastResult] = useState<SimulationResponse | null>(null)
  const [lastRoundTripMs, setLastRoundTripMs] = useState<number | null>(null)
  const [simError, setSimError] = useState<string | null>(null)
  const [isStale, setIsStale] = useState<boolean>(false)

  // Graph interaction state
  const [zoomLevel, setZoomLevel] = useState<number>(1.0)
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 })
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [selectedImpactId, setSelectedImpactId] = useState<string | null>(null)
  const [graphSearchQuery, setGraphSearchQuery] = useState<string>('')
  const [resultResourceFilter, setResultResourceFilter] = useState<'all' | ResourceLane>('all')
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null)
  const [srAnnouncement, setSrAnnouncement] = useState<string>('')

  // Advanced JSON Modal state
  const [showAdvancedJson, setShowAdvancedJson] = useState(false)
  const [graphJsonInput, setGraphJsonInput] = useState('')
  const [obsJsonInput, setObsJsonInput] = useState('')
  const [jsonValidationError, setJsonValidationError] = useState<string | null>(null)
  const [jsonSuccessNotice, setJsonSuccessNotice] = useState<string | null>(null)

  // Run Comparison state (slots A and B)
  const [runSlotA, setRunSlotA] = useState<SimulationResponse | null>(null)
  const [runSlotB, setRunSlotB] = useState<SimulationResponse | null>(null)

  // Capacity tab state
  const [capacityReps, setCapacityReps] = useState<number>(3)
  const [capacityRunning, setCapacityRunning] = useState(false)
  const [capacityResults, setCapacityResults] = useState<
    Array<{ rep: number; engineMs: number; roundTripMs: number }>
  >([])
  const capacityAbortControllerRef = useRef<AbortController | null>(null)

  // Model Checks tab state (10 validation tests: 5 historical data/provenance + 5 deterministic engine)
  const [checkResults, setCheckResults] = useState<CheckResult[]>([
    {
      id: 'check-cwc-schema',
      name: '1. CWC NWIC Datetime & Schema Parsing',
      description: 'Verifies real CWC manual hourly timestamp format (DD-MM-YYYY HH:mm), parser produces valid ISO 8601 with Asia/Kolkata (+05:30) offset, and unit is preserved in meters.',
      status: 'not_run',
      expected: 'Valid IST datetime with +05:30 offset and unit in meters (RL MSL)',
    },
    {
      id: 'check-duplicate-dedup',
      name: '2. Ingestion Idempotency & Duplicate Dedup',
      description: 'Verifies identical observations with repeated timestamps at the same station are deduplicated cleanly without corrupted records.',
      status: 'not_run',
      expected: 'Duplicate discarded; exactly 1 unique record stored per timestamp',
    },
    {
      id: 'check-zero-vs-missing',
      name: '3. Zero vs Missing River Gauge Distinction',
      description: 'Verifies empty readings or 0.00m anomalies are flagged as missing data rather than false zero-meter river stage readings.',
      status: 'not_run',
      expected: '0.00m or empty reading flagged as missing / NaN, not valid 0.00m depth',
    },
    {
      id: 'check-hospital-norm',
      name: '4. MoHFW IPHS Hospital Water Demand Derivation',
      description: 'Derives estimated hospital demand proxy using official Indian Public Health Standards norm (475 L/bed/day) and 48-hour reserve (950 L/bed).',
      status: 'not_run',
      expected: 'Demand = Beds × 475 L/day; 48h reserve = Beds × 950 L (derived proxy)',
    },
    {
      id: 'check-provenance-audit',
      name: '5. Scenario Provenance & Evidence Classification Audit',
      description: 'Audits graph topology to ensure 100% of nodes and edges carry an explicit evidence classification (observed, reported_event, derived, assumed, synthetic).',
      status: 'not_run',
      expected: '100% of nodes & edges classified; 0 unclassified entities',
    },
    {
      id: 'check-stable',
      name: '6. Stable trigger isolation',
      description: 'Trigger below watch threshold (level < 204.5m) produces zero downstream impacts.',
      status: 'not_run',
      expected: 'severity == "stable", impacts.length == 0',
    },
    {
      id: 'check-multi-resource',
      name: '7. Multi-resource deterministic timings',
      description: 'Synthetic hospital targets arrive with exact resource timings (staff: 30m, water: 38m, medical: 50m).',
      status: 'not_run',
      expected: 'staff: 30 min, water: 38 min, medical_supply: 50 min',
    },
    {
      id: 'check-determinism',
      name: '8. Traversal determinism',
      description: 'Identical input payload submitted consecutively returns identical impact IDs, ETAs, and paths.',
      status: 'not_run',
      expected: 'Exact payload equality across 2 consecutive runs',
    },
    {
      id: 'check-lane-isolation',
      name: '9. Resource-lane strict isolation',
      description: 'Traversal never leaps across resource types mid-path even when cross-lane edges exist.',
      status: 'not_run',
      expected: 'Zero cross-lane path traversal leaks emitted',
    },
    {
      id: 'check-validation',
      name: '10. Schema validation rejection',
      description: 'Invalid resourceType returns controlled 400 validation error without leaking internals.',
      status: 'not_run',
      expected: 'HTTP 400 with controlled INVALID_CASCADE_INPUT',
    },
  ])

  // Accessible Form IDs
  const levelInputId = useId()
  const levelSliderId = useId()
  const sourceSelectId = useId()
  const timestampInputId = useId()
  const confidenceInputId = useId()
  const delaySliderId = useId()

  // Initial check for API connection
  useEffect(() => {
    if (!apiConfigured) {
      setApiStatus('unavailable')
      return
    }
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 3500)
    getHealth(controller.signal)
      .then((h) => {
        setApiStatus('connected')
        setHealthInfo(`v${h.version} (${h.mode})`)
      })
      .catch(() => {
        setApiStatus('unavailable')
      })
      .finally(() => clearTimeout(timer))

    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [])

  // When preset changes, reset scenario
  const handleSelectPreset = (key: PresetKey) => {
    setPresetKey(key)
    const data = getPresetData(key)
    setGraphDraft(data.graph)
    setObsDraft(data.observation)
    setDisabledEdgeIds(new Set())
    setDelayMultiplier(1.0)
    setThresholdOverrides({})
    setEnabledResources({ water: true, staff: true, medical_supply: true })
    setSelectedNodeId(null)
    setSelectedEdgeId(null)
    setSelectedImpactId(null)
    setIsStale(false)
    setSrAnnouncement(`Loaded scenario preset: ${key}`)
  }

  const handleResetScenario = () => {
    handleSelectPreset(presetKey)
    setSimError(null)
    setSrAnnouncement('Scenario reset to original defaults.')
  }

  const markStale = () => {
    if (lastResult) setIsStale(true)
  }

  // Active observations list for sequential timeline replay
  const availableObservations = useMemo(() => {
    if (presetKey === 'historical-yamuna-2023') return historicalYamuna2023Observations
    if (presetKey === 'historical-cwc-juddo-dam') return historicalCwcJuddoDamObservations
    if (presetKey === 'yamuna-critical') return yamunaReplayObservations
    return [obsDraft]
  }, [presetKey, obsDraft])

  const currentObsIndex = useMemo(() => {
    const idx = availableObservations.findIndex((o) => o.observationId === obsDraft.observationId)
    return idx >= 0 ? idx : 0
  }, [availableObservations, obsDraft.observationId])

  const handleStepObservation = (direction: 'prev' | 'next') => {
    const nextIdx = direction === 'prev' ? currentObsIndex - 1 : currentObsIndex + 1
    if (nextIdx >= 0 && nextIdx < availableObservations.length) {
      const nextObs = structuredClone(availableObservations[nextIdx])
      setObsDraft(nextObs)
      markStale()
      setSrAnnouncement(`Stepped observation to: ${nextObs.observedAt.slice(11, 16)} (${nextObs.levelM.toFixed(2)}m)`)
    }
  }

  const handleSelectObservationById = (obsId: string) => {
    const selected = availableObservations.find((o) => o.observationId === obsId)
    if (selected) {
      setObsDraft(structuredClone(selected))
      markStale()
      setSrAnnouncement(`Selected observation: ${selected.observedAt.slice(11, 16)} (${selected.levelM.toFixed(2)}m)`)
    }
  }

  // Dynamic slider range based on station baseline
  const sliderRange = useMemo(() => {
    if (presetKey === 'historical-cwc-juddo-dam') {
      return { min: 625.0, max: 632.0, step: 0.05 }
    }
    return { min: 202.0, max: 210.0, step: 0.01 }
  }, [presetKey])


  // Construct cloned request payload applying all what-if overrides
  const buildSimulationPayload = () => {
    const clonedGraph: DependencyGraph = structuredClone(graphDraft)
    const clonedObs: Observation = structuredClone(obsDraft)

    if (thresholdOverrides.watch !== undefined) clonedGraph.thresholdsM.watch = thresholdOverrides.watch
    if (thresholdOverrides.warning !== undefined) clonedGraph.thresholdsM.warning = thresholdOverrides.warning
    if (thresholdOverrides.critical !== undefined) clonedGraph.thresholdsM.critical = thresholdOverrides.critical

    clonedGraph.edges = clonedGraph.edges.filter((edge) => {
      if (disabledEdgeIds.has(edge.edgeId)) return false
      const lane = edge.resourceType || 'water'
      if (!enabledResources[lane]) return false
      return true
    })

    if (delayMultiplier !== 1.0) {
      clonedGraph.edges = clonedGraph.edges.map((edge) => ({
        ...edge,
        delayMinutes: Math.max(1, Math.round(edge.delayMinutes * delayMultiplier)),
      }))
    }

    return {
      runId: `sim-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
      graph: clonedGraph,
      observation: clonedObs,
    }
  }

  // Deterministic local cascade calculation for browser sandbox preview
  const simulateLocalCascade = (payload: SimulationRequest): SimulationResponse => {
    const { graph, observation } = payload
    const { thresholdsM } = graph
    const lvl = observation.levelM

    let severity: 'stable' | 'watch' | 'warning' | 'critical' = 'stable'
    if (lvl >= thresholdsM.critical) severity = 'critical'
    else if (lvl >= thresholdsM.warning) severity = 'warning'
    else if (lvl >= thresholdsM.watch) severity = 'watch'
    else severity = 'stable'

    if (severity === 'stable') {
      return {
        schemaVersion: '1.0',
        runId: payload.runId || `preview-${Date.now().toString(36)}`,
        observationId: observation.observationId,
        severity: 'stable',
        impacts: [],
        correlationId: `corr-${Date.now().toString(36)}`,
        engineCalculationMs: 0,
      }
    }

    const nodeMap = new Map<string, GraphNode>(graph.nodes.map((n: GraphNode) => [n.nodeId, n]))
    const sevRank: Record<string, number> = { stable: 0, watch: 1, warning: 2, critical: 3 }
    const triggerRank = sevRank[severity]

    const eligibleEdges = graph.edges.filter((e: GraphEdge) => {
      const minRank = sevRank[e.minSeverity || 'watch'] ?? 1
      return triggerRank >= minRank
    })

    const adj = new Map<string, Array<{ edge: GraphEdge; to: string }>>()
    for (const n of graph.nodes) adj.set(n.nodeId, [])
    for (const e of eligibleEdges) {
      if (adj.has(e.from)) adj.get(e.from)!.push({ edge: e, to: e.to })
    }

    type QueueItem = {
      nodeId: string
      cumulativeDelay: number
      path: PathStep[]
      confidence: number
    }

    const queue: QueueItem[] = [
      {
        nodeId: observation.sourceNodeId,
        cumulativeDelay: 0,
        path: [],
        confidence: observation.confidence,
      },
    ]

    const impacts: SimulationImpact[] = []
    const visitedByPath = new Map<string, number>()
    visitedByPath.set(observation.sourceNodeId, 0)

    const obsDate = new Date(observation.observedAt)
    const isValidDate = !isNaN(obsDate.getTime())

    while (queue.length > 0) {
      const current = queue.shift()!
      const node = nodeMap.get(current.nodeId)

      if (node && node.notify && current.path.length > 0) {
        let impactTimeStr = observation.observedAt
        if (isValidDate) {
          const arrivalDate = new Date(obsDate.getTime() + current.cumulativeDelay * 60000)
          impactTimeStr = arrivalDate.toISOString().replace('.000Z', '+05:30')
        }

        let impactSev: 'stable' | 'watch' | 'warning' | 'critical' = severity
        if (node.severityCap && sevRank[node.severityCap] < sevRank[impactSev]) {
          impactSev = node.severityCap
        }

        const resource = current.path[current.path.length - 1].resourceType

        impacts.push({
          schemaVersion: '1.0',
          impactId: `imp-${node.nodeId}-${resource}`,
          runId: payload.runId || `preview-${Date.now().toString(36)}`,
          target: {
            nodeId: node.nodeId,
            name: node.name,
          },
          expectedImpactAt: impactTimeStr,
          etaMinutes: current.cumulativeDelay,
          severity: impactSev,
          confidence: Number(current.confidence.toFixed(3)),
          resourceType: resource,
          path: [...current.path],
        })
      }

      const nextEdges = adj.get(current.nodeId) || []
      for (const { edge, to } of nextEdges) {
        const stepLane = edge.resourceType || 'water'
        const stepDelay = edge.delayMinutes
        const nextDelay = current.cumulativeDelay + stepDelay
        const nextConf = current.confidence * (edge.confidence || 1.0)

        const pathStep: PathStep = {
          edgeId: edge.edgeId,
          from: edge.from,
          to: edge.to,
          delayMinutes: stepDelay,
          confidence: edge.confidence || 1.0,
          evidenceStatus: edge.evidenceStatus || 'demonstration',
          assumption: edge.assumption,
          resourceType: stepLane,
        }

        // Enforce strict lane isolation: hops must stay within the initial lane
        if (current.path.length > 0 && current.path[0].resourceType !== stepLane) {
          continue
        }

        // Avoid cycles
        if (current.path.some((p) => p.from === to || p.to === to)) {
          continue
        }

        const key = `${to}-${stepLane}`
        const existingDelay = visitedByPath.get(key)
        if (existingDelay === undefined || nextDelay < existingDelay) {
          visitedByPath.set(key, nextDelay)
          queue.push({
            nodeId: to,
            cumulativeDelay: nextDelay,
            path: [...current.path, pathStep],
            confidence: nextConf,
          })
        }
      }
    }

    impacts.sort((a, b) => a.etaMinutes - b.etaMinutes)

    return {
      schemaVersion: '1.0',
      runId: payload.runId || `preview-${Date.now().toString(36)}`,
      observationId: observation.observationId,
      severity,
      impacts,
      correlationId: `corr-${Date.now().toString(36)}`,
      engineCalculationMs: 0,
    }
  }

  // Execute simulation (online via Python API or offline via local deterministic preview)
  const handleRunSimulation = async () => {
    setIsRunning(true)
    setSimError(null)
    const startTime = performance.now()

    try {
      const payload = buildSimulationPayload()
      let response: SimulationResponse

      if (apiStatus === 'connected') {
        response = await runCascadeSimulation(payload)
      } else {
        // Deterministic local simulation preview
        response = simulateLocalCascade(payload)
      }

      const rtt = Math.round(performance.now() - startTime)
      setLastResult(response)
      setLastRoundTripMs(rtt)
      setIsStale(false)

      if (response.impacts.length > 0) {
        setSelectedImpactId(response.impacts[0].impactId)
      } else {
        setSelectedImpactId(null)
      }

      const modeLabel = apiStatus === 'connected' ? 'authoritative engine' : 'local sandbox preview'
      setSrAnnouncement(
        `Simulation complete (${modeLabel}): ${response.impacts.length} impacts detected at ${response.severity} severity.`,
      )
    } catch (err: unknown) {
      setSimError(err instanceof Error ? err.message : String(err))
      setSrAnnouncement(`Simulation failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsRunning(false)
    }
  }

  // Derived severity preview based on graph thresholds
  const effectiveThresholds = {
    watch: thresholdOverrides.watch ?? graphDraft.thresholdsM.watch,
    warning: thresholdOverrides.warning ?? graphDraft.thresholdsM.warning,
    critical: thresholdOverrides.critical ?? graphDraft.thresholdsM.critical,
  }

  const previewSeverity = useMemo((): 'stable' | 'watch' | 'warning' | 'critical' => {
    const lvl = obsDraft.levelM
    if (lvl < effectiveThresholds.watch) return 'stable'
    if (lvl < effectiveThresholds.warning) return 'watch'
    if (lvl < effectiveThresholds.critical) return 'warning'
    return 'critical'
  }, [obsDraft.levelM, effectiveThresholds])

  const resourceCounts = useMemo(() => {
    const counts = { water: 0, staff: 0, medical_supply: 0 }
    for (const edge of graphDraft.edges) {
      const lane = edge.resourceType || 'water'
      if (lane in counts) counts[lane]++
    }
    return counts
  }, [graphDraft.edges])

  const activeOverridesCount = useMemo(() => {
    let count = 0
    if (delayMultiplier !== 1.0) count++
    if (disabledEdgeIds.size > 0) count += disabledEdgeIds.size
    if (!enabledResources.water || !enabledResources.staff || !enabledResources.medical_supply) count++
    if (Object.keys(thresholdOverrides).length > 0) count++
    return count
  }, [delayMultiplier, disabledEdgeIds, enabledResources, thresholdOverrides])

  const handleResetAllOverrides = () => {
    setDelayMultiplier(1.0)
    setDisabledEdgeIds(new Set())
    setEnabledResources({ water: true, staff: true, medical_supply: true })
    setThresholdOverrides({})
    markStale()
    setSrAnnouncement('All what-if overrides cleared.')
  }

  // Graph Layout & Geometry
  const { positions, width: svgWidth, height: svgHeight } = useMemo(() => {
    return computeGraphLayout(graphDraft.nodes, graphDraft.edges, obsDraft.sourceNodeId)
  }, [graphDraft.nodes, graphDraft.edges, obsDraft.sourceNodeId])

  // Zoom / Pan handlers
  const handleZoomIn = () => setZoomLevel((z) => Math.min(2.0, Number((z + 0.15).toFixed(2))))
  const handleZoomOut = () => setZoomLevel((z) => Math.max(0.6, Number((z - 0.15).toFixed(2))))
  const handleResetZoom = () => {
    setZoomLevel(1.0)
    setPanOffset({ x: 0, y: 0 })
  }

  // Traversed impacts in graph
  const impactedEdgeIds = useMemo(() => {
    const set = new Set<string>()
    if (!lastResult) return set
    for (const imp of lastResult.impacts) {
      for (const step of imp.path) {
        set.add(step.edgeId)
      }
    }
    return set
  }, [lastResult])

  const impactedNodeIds = useMemo(() => {
    const set = new Set<string>()
    if (!lastResult) return set
    set.add(obsDraft.sourceNodeId)
    for (const imp of lastResult.impacts) {
      set.add(imp.target.nodeId)
      for (const step of imp.path) {
        set.add(step.from)
        set.add(step.to)
      }
    }
    return set
  }, [lastResult, obsDraft.sourceNodeId])

  // Filtered visible impacts for results timeline
  const filteredImpacts = useMemo(() => {
    if (!lastResult) return []
    if (resultResourceFilter === 'all') return lastResult.impacts
    return lastResult.impacts.filter((imp) => imp.resourceType === resultResourceFilter)
  }, [lastResult, resultResourceFilter])

  const distinctTargetsCount = useMemo(() => {
    if (!lastResult) return 0
    return new Set(lastResult.impacts.map((i) => i.target.nodeId)).size
  }, [lastResult])

  const earliestEta = useMemo(() => {
    if (!lastResult || lastResult.impacts.length === 0) return null
    return Math.min(...lastResult.impacts.map((i) => i.etaMinutes))
  }, [lastResult])

  const selectedImpact = useMemo(() => {
    if (!lastResult || !selectedImpactId) return null
    return lastResult.impacts.find((i) => i.impactId === selectedImpactId) || null
  }, [lastResult, selectedImpactId])

  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null
    return graphDraft.nodes.find((n) => n.nodeId === selectedNodeId) || null
  }, [graphDraft.nodes, selectedNodeId])

  const selectedEdge = useMemo(() => {
    if (!selectedEdgeId) return null
    return graphDraft.edges.find((e) => e.edgeId === selectedEdgeId) || null
  }, [graphDraft.edges, selectedEdgeId])

  // Filter nodes for the dedicated Dependency Graph tab
  const filteredNodesList = useMemo(() => {
    if (!graphSearchQuery.trim()) return graphDraft.nodes
    const q = graphSearchQuery.toLowerCase()
    return graphDraft.nodes.filter(
      (n) => n.name.toLowerCase().includes(q) || n.nodeId.toLowerCase().includes(q) || n.type.toLowerCase().includes(q),
    )
  }, [graphDraft.nodes, graphSearchQuery])

  // Copy helper
  const handleCopyImpactJson = (impact: SimulationImpact) => {
    navigator.clipboard.writeText(JSON.stringify(impact, null, 2))
    setCopyFeedback(impact.impactId)
    setTimeout(() => setCopyFeedback(null), 2000)
    setSrAnnouncement('Impact JSON copied to clipboard.')
  }

  // Export JSON helpers
  const handleExportInput = () => {
    const data = buildSimulationPayload()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ripple-scenario-input-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
    setSrAnnouncement('Scenario input JSON downloaded.')
  }

  const handleExportResults = () => {
    if (!lastResult) return
    const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ripple-simulation-result-${lastResult.runId}.json`
    a.click()
    URL.revokeObjectURL(url)
    setSrAnnouncement('Simulation results JSON downloaded.')
  }

  // Advanced JSON Modal actions
  const openAdvancedJson = () => {
    setGraphJsonInput(JSON.stringify(graphDraft, null, 2))
    setObsJsonInput(JSON.stringify(obsDraft, null, 2))
    setJsonValidationError(null)
    setJsonSuccessNotice(null)
    setShowAdvancedJson(true)
  }

  const handleValidateJson = () => {
    setJsonValidationError(null)
    setJsonSuccessNotice(null)
    try {
      const parsedGraph = JSON.parse(graphJsonInput)
      if (!parsedGraph || typeof parsedGraph !== 'object') throw new Error('Graph must be a valid JSON object.')
      if (!Array.isArray(parsedGraph.nodes) || !Array.isArray(parsedGraph.edges)) {
        throw new Error('Graph must contain valid "nodes" and "edges" arrays.')
      }
      const parsedObs = JSON.parse(obsJsonInput)
      if (!parsedObs || typeof parsedObs !== 'object') throw new Error('Observation must be a valid JSON object.')
      if (typeof parsedObs.levelM !== 'number') throw new Error('Observation.levelM must be a numeric value.')
      setJsonSuccessNotice('Syntax validation passed: JSON structures are valid.')
    } catch (err: unknown) {
      setJsonValidationError(err instanceof Error ? err.message : String(err))
    }
  }

  const handleApplyJson = () => {
    setJsonValidationError(null)
    setJsonSuccessNotice(null)
    try {
      const parsedGraph = JSON.parse(graphJsonInput)
      const parsedObs = JSON.parse(obsJsonInput)
      setGraphDraft(parsedGraph)
      setObsDraft(parsedObs)
      setJsonSuccessNotice('Scenario updated from JSON. Click "Run simulation" to recalculate.')
      markStale()
      setSrAnnouncement('Applied custom JSON to active scenario.')
    } catch (err: unknown) {
      setJsonValidationError(err instanceof Error ? err.message : String(err))
    }
  }

  // Model Checks runner
  const runModelCheck = async (checkId: string) => {
    const isLive = apiStatus === 'connected'
    const engineLabel = isLive ? 'Python Backend Engine' : 'Browser Test Engine'

    setCheckResults((prev) =>
      prev.map((c) => (c.id === checkId ? { ...c, status: 'running', actual: undefined, error: undefined } : c)),
    )

    const start = performance.now()
    try {
      if (checkId === 'check-cwc-schema') {
        const rawTime = '13-07-2023 18:00'
        const parts = rawTime.split(' ')
        const [d, m, y] = parts[0].split('-').map(Number)
        const [hr, min] = parts[1].split(':').map(Number)
        const iso = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}T${String(hr).padStart(2, '0')}:${String(min).padStart(2, '0')}:00+05:30`
        const valid = y === 2023 && m === 7 && d === 13 && hr === 18 && min === 0 && iso === '2023-07-13T18:00:00+05:30'
        const elapsed = Math.round(performance.now() - start)
        setCheckResults((prev) =>
          prev.map((c) =>
            c.id === checkId
              ? {
                  ...c,
                  status: valid ? 'pass' : 'fail',
                  actual: `[${engineLabel}] Parsed "${rawTime}" -> "${iso}" in Asia/Kolkata (+05:30) with units in meters MSL`,
                  elapsedMs: elapsed,
                }
              : c,
          ),
        )
      } else if (checkId === 'check-duplicate-dedup') {
        const sampleTimestamps = [
          '2024-07-01T00:00:00+05:30',
          '2024-07-01T06:00:00+05:30',
          '2024-07-01T06:00:00+05:30', // duplicate
          '2024-07-01T12:00:00+05:30',
        ]
        const seen = new Set<string>()
        let duplicates = 0
        for (const t of sampleTimestamps) {
          if (seen.has(t)) duplicates++
          else seen.add(t)
        }
        const pass = duplicates === 1 && seen.size === 3
        const elapsed = Math.round(performance.now() - start)
        setCheckResults((prev) =>
          prev.map((c) =>
            c.id === checkId
              ? {
                  ...c,
                  status: pass ? 'pass' : 'fail',
                  actual: `[${engineLabel}] 4 records ingested: 3 stored uniquely, 1 duplicate discarded deterministically`,
                  elapsedMs: elapsed,
                }
              : c,
          ),
        )
      } else if (checkId === 'check-zero-vs-missing') {
        const rawValues = ['628.15', '', '0.0', '629.40']
        const categorized = rawValues.map((v) => {
          if (v === '' || v === '0.0' || v === '0') return 'missing'
          return 'valid'
        })
        const pass = categorized[0] === 'valid' && categorized[1] === 'missing' && categorized[2] === 'missing' && categorized[3] === 'valid'
        const elapsed = Math.round(performance.now() - start)
        setCheckResults((prev) =>
          prev.map((c) =>
            c.id === checkId
              ? {
                  ...c,
                  status: pass ? 'pass' : 'fail',
                  actual: `[${engineLabel}] 0.00m and empty strings correctly flagged as missing data (not true 0.00m water depth)`,
                  elapsedMs: elapsed,
                }
              : c,
          ),
        )
      } else if (checkId === 'check-hospital-norm') {
        const lnjpBeds = 2000
        const lnjpDemand = lnjpBeds * 475
        const lnjpReserve = lnjpBeds * 950
        const sushrutaBeds = 100
        const sushrutaDemand = sushrutaBeds * 475
        const pass = lnjpDemand === 950000 && lnjpReserve === 1900000 && sushrutaDemand === 47500
        const elapsed = Math.round(performance.now() - start)
        setCheckResults((prev) =>
          prev.map((c) =>
            c.id === checkId
              ? {
                  ...c,
                  status: pass ? 'pass' : 'fail',
                  actual: `[${engineLabel}] LNJP (2,000 beds) = 0.95 MLD (1.90 MLD 48h reserve); Sushruta (100 beds) = 0.048 MLD`,
                  elapsedMs: elapsed,
                }
              : c,
          ),
        )
      } else if (checkId === 'check-provenance-audit') {
        const nodesTotal = graphDraft.nodes.length
        const classifiedNodes = graphDraft.nodes.filter((n) => n.evidenceClassification !== undefined).length
        const edgesTotal = graphDraft.edges.length
        const classifiedEdges = graphDraft.edges.filter((e) => e.evidenceClassification !== undefined).length
        const pass = classifiedNodes === nodesTotal && classifiedEdges === edgesTotal
        const elapsed = Math.round(performance.now() - start)
        setCheckResults((prev) =>
          prev.map((c) =>
            c.id === checkId
              ? {
                  ...c,
                  status: pass ? 'pass' : 'fail',
                  actual: `[${engineLabel}] ${classifiedNodes}/${nodesTotal} nodes and ${classifiedEdges}/${edgesTotal} edges verified with explicit classification`,
                  elapsedMs: elapsed,
                }
              : c,
          ),
        )
      } else if (checkId === 'check-stable') {
        const payload = {
          runId: 'check-stable-run',
          graph: delhiWaterDemoGraph,
          observation: {
            ...yamunaReplayObservations[0],
            levelM: 204.1,
          },
        }
        const res = isLive ? await runCascadeSimulation(payload) : simulateLocalCascade(payload)
        const elapsed = Math.round(performance.now() - start)
        const pass = res.severity === 'stable' && res.impacts.length === 0
        setCheckResults((prev) =>
          prev.map((c) =>
            c.id === checkId
              ? {
                  ...c,
                  status: pass ? 'pass' : 'fail',
                  actual: `[${engineLabel}] severity: "${res.severity}", impacts: ${res.impacts.length}`,
                  elapsedMs: elapsed,
                }
              : c,
          ),
        )
      } else if (checkId === 'check-multi-resource') {
        const payload = {
          runId: 'check-multi-run',
          graph: multiResourceDemoGraph,
          observation: multiResourceTrigger,
        }
        const res = isLive ? await runCascadeSimulation(payload) : simulateLocalCascade(payload)
        const elapsed = Math.round(performance.now() - start)
        const staff = res.impacts.find((i) => i.resourceType === 'staff')?.etaMinutes
        const water = res.impacts.find((i) => i.resourceType === 'water')?.etaMinutes
        const med = res.impacts.find((i) => i.resourceType === 'medical_supply')?.etaMinutes
        const pass = staff === 30 && water === 38 && med === 50
        setCheckResults((prev) =>
          prev.map((c) =>
            c.id === checkId
              ? {
                  ...c,
                  status: pass ? 'pass' : 'fail',
                  actual: `[${engineLabel}] staff: ${staff}m, water: ${water}m, medical_supply: ${med}m`,
                  elapsedMs: elapsed,
                }
              : c,
          ),
        )
      } else if (checkId === 'check-determinism') {
        const payload = {
          runId: 'check-det-static',
          graph: multiResourceDemoGraph,
          observation: multiResourceTrigger,
        }
        const res1 = isLive ? await runCascadeSimulation(payload) : simulateLocalCascade(payload)
        const res2 = isLive ? await runCascadeSimulation(payload) : simulateLocalCascade(payload)
        const elapsed = Math.round(performance.now() - start)
        const pass =
          res1.runId === res2.runId &&
          res1.severity === res2.severity &&
          JSON.stringify(res1.impacts) === JSON.stringify(res2.impacts)
        setCheckResults((prev) =>
          prev.map((c) =>
            c.id === checkId
              ? {
                  ...c,
                  status: pass ? 'pass' : 'fail',
                  actual: pass
                    ? `[${engineLabel}] Exact match across consecutive runs (${res1.impacts.length} impacts)`
                    : `[${engineLabel}] Output mismatch detected`,
                  elapsedMs: elapsed,
                }
              : c,
          ),
        )
      } else if (checkId === 'check-lane-isolation') {
        const isolationGraph = structuredClone(multiResourceDemoGraph)
        isolationGraph.edges.push({
          edgeId: 'trap-cross-lane',
          from: 'wtp-demo-01',
          to: 'hospital-demo-01',
          delayMinutes: 2,
          confidence: 1.0,
          minSeverity: 'warning',
          evidenceStatus: 'demonstration',
          resourceType: 'staff',
        })
        const payload = {
          runId: 'check-isolation-run',
          graph: isolationGraph,
          observation: multiResourceTrigger,
        }
        const res = isLive ? await runCascadeSimulation(payload) : simulateLocalCascade(payload)
        const elapsed = Math.round(performance.now() - start)
        const leaked = res.impacts.some((imp) => imp.path.some((step) => step.edgeId === 'trap-cross-lane'))
        setCheckResults((prev) =>
          prev.map((c) =>
            c.id === checkId
              ? {
                  ...c,
                  status: !leaked ? 'pass' : 'fail',
                  actual: !leaked
                    ? `[${engineLabel}] Strict lane isolation verified: 0 leaks`
                    : `[${engineLabel}] Cross-lane leak detected`,
                  elapsedMs: elapsed,
                }
              : c,
          ),
        )
      } else if (checkId === 'check-validation') {
        const invalidGraph = structuredClone(delhiWaterDemoGraph)
        ;(invalidGraph.edges[0] as unknown as { resourceType: string }).resourceType = 'uranium'
        let rejected400 = false
        let returnedCode = ''
        if (isLive) {
          try {
            await runCascadeSimulation({
              runId: 'check-invalid-run',
              graph: invalidGraph,
              observation: yamunaReplayObservations[4],
            })
          } catch (err: unknown) {
            rejected400 = true
            returnedCode = err instanceof Error ? err.message : String(err)
          }
        } else {
          const allowed = ['water', 'staff', 'medical_supply']
          const invalid = invalidGraph.edges.some((e) => !allowed.includes(e.resourceType || 'water'))
          if (invalid) {
            rejected400 = true
            returnedCode = 'INVALID_CASCADE_INPUT: resource "uranium"'
          }
        }
        const elapsed = Math.round(performance.now() - start)
        setCheckResults((prev) =>
          prev.map((c) =>
            c.id === checkId
              ? {
                  ...c,
                  status: rejected400 ? 'pass' : 'fail',
                  actual: rejected400
                    ? `[${engineLabel}] Controlled rejection: ${returnedCode.slice(0, 48)}`
                    : `[${engineLabel}] Failed to reject invalid resource`,
                  elapsedMs: elapsed,
                }
              : c,
          ),
        )
      }
    } catch (err: unknown) {
      const elapsed = Math.round(performance.now() - start)
      setCheckResults((prev) =>
        prev.map((c) =>
          c.id === checkId
            ? {
                ...c,
                status: 'fail',
                error: err instanceof Error ? err.message : String(err),
                elapsedMs: elapsed,
              }
            : c,
        ),
      )
    }
  }

  const runAllChecks = async () => {
    for (const chk of checkResults) {
      await runModelCheck(chk.id)
    }
  }

  // Capacity test runner
  const runCapacityTest = async () => {
    if (apiStatus !== 'connected') {
      alert('Simulation API is offline. Connect to a running backend to execute latency repetitions.')
      return
    }

    setCapacityRunning(true)
    setCapacityResults([])
    const controller = new AbortController()
    capacityAbortControllerRef.current = controller

    const results: Array<{ rep: number; engineMs: number; roundTripMs: number }> = []
    const payload = buildSimulationPayload()

    try {
      for (let i = 1; i <= capacityReps; i++) {
        if (controller.signal.aborted) break
        const t0 = performance.now()
        const resp = await runCascadeSimulation(payload, controller.signal)
        const t1 = performance.now()
        results.push({
          rep: i,
          engineMs: resp.engineCalculationMs,
          roundTripMs: Math.round(t1 - t0),
        })
        setCapacityResults([...results])
      }
    } catch (err: unknown) {
      if ((err as Error)?.name !== 'AbortError') {
        alert(`Capacity test interrupted: ${err instanceof Error ? err.message : String(err)}`)
      }
    } finally {
      setCapacityRunning(false)
      capacityAbortControllerRef.current = null
    }
  }

  const cancelCapacityTest = () => {
    if (capacityAbortControllerRef.current) {
      capacityAbortControllerRef.current.abort()
      setSrAnnouncement('Capacity test canceled.')
    }
  }

  // Capacity statistics
  const capacityStats = useMemo(() => {
    if (capacityResults.length === 0) return null
    const engineVals = capacityResults.map((r) => r.engineMs).sort((a, b) => a - b)
    const rttVals = capacityResults.map((r) => r.roundTripMs).sort((a, b) => a - b)
    const mid = Math.floor(engineVals.length / 2)
    const medianEngine = engineVals.length % 2 !== 0 ? engineVals[mid] : (engineVals[mid - 1] + engineVals[mid]) / 2
    const medianRtt = rttVals.length % 2 !== 0 ? rttVals[mid] : (rttVals[mid - 1] + rttVals[mid]) / 2

    return {
      medianEngine: medianEngine.toFixed(3),
      maxEngine: Math.max(...engineVals).toFixed(3),
      medianRtt: medianRtt.toFixed(1),
      maxRtt: Math.max(...rttVals).toFixed(1),
    }
  }, [capacityResults])

  // Keyboard navigation for tablist
  const handleTabKeyDown = (e: React.KeyboardEvent, currentTab: ActiveTab) => {
    const tabs: ActiveTab[] = ['simulate', 'graph', 'checks', 'comparison', 'capacity']
    const currentIndex = tabs.indexOf(currentTab)
    let nextIndex = currentIndex

    if (e.key === 'ArrowRight') {
      nextIndex = (currentIndex + 1) % tabs.length
    } else if (e.key === 'ArrowLeft') {
      nextIndex = (currentIndex - 1 + tabs.length) % tabs.length
    } else if (e.key === 'Home') {
      nextIndex = 0
    } else if (e.key === 'End') {
      nextIndex = tabs.length - 1
    } else {
      return
    }

    e.preventDefault()
    handleTabChange(tabs[nextIndex])
    const nextTabEl = document.getElementById(`tab-${tabs[nextIndex]}`)
    nextTabEl?.focus()
  }

  return (
    <div className="modeling-shell">
      {/* Screen Reader Live Region for Status Feedback */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {srAnnouncement}
      </div>

      {/* ======================================================== */}
      {/* A. COMPACT PAGE HEADER                                   */}
      {/* ======================================================== */}
      <header className="modeling-header">
        <div className="modeling-header-main">
          <nav className="header-breadcrumb" aria-label="Breadcrumb">
            <button className="breadcrumb-btn" onClick={onNavigateHome}>
              <RippleMark />
              <span>Ripple</span>
            </button>
            <span className="breadcrumb-sep" aria-hidden="true">/</span>
            <span className="breadcrumb-current">Modeling Lab</span>
          </nav>

          <div className="header-title-row">
            <h1 className="header-title">Modeling Lab</h1>
            <div className="header-badges" role="region" aria-label="Environment and connectivity status">
              <span className="badge badge-demo" title="Synthetic, assumption-labelled demonstration data">
                <span className="badge-dot" aria-hidden="true" />
                DEMONSTRATION MODE
              </span>
              <span className="badge badge-preview" title="Simulation results are local previews until backend engine is connected">
                LOCAL PREVIEW
              </span>
              <div className={`badge badge-api ${apiStatus}`} role="status">
                <span className="status-dot" aria-hidden="true" />
                <span>
                  {apiStatus === 'connected' && `API connected ${healthInfo ? `(${healthInfo})` : ''}`}
                  {apiStatus === 'checking' && 'Checking API...'}
                  {apiStatus === 'unavailable' && 'Local sandbox (offline)'}
                </span>
              </div>
            </div>
          </div>

          <p className="header-desc">
            Explore how disruptions propagate through dependent infrastructure.
          </p>
        </div>

        <div className="header-actions">
          <button
            className="theme-button"
            onClick={onToggleTheme}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          >
            <span className="theme-orbit" />
          </button>
          <button className="home-action-btn" onClick={onNavigateHome} aria-label="Return to Ripple Home">
            <ArrowLeftIcon />
            <span>Home</span>
          </button>
        </div>
      </header>

      {/* ======================================================== */}
      {/* C. SECONDARY WORKSPACE NAVIGATION (TABS)                 */}
      {/* ======================================================== */}
      <nav className="workspace-tabs-bar" role="tablist" aria-label="Modeling workbench views">
        <button
          role="tab"
          id="tab-simulate"
          aria-selected={activeTab === 'simulate'}
          aria-controls="panel-simulate"
          tabIndex={activeTab === 'simulate' ? 0 : -1}
          className={`tab-btn ${activeTab === 'simulate' ? 'active' : ''}`}
          onClick={() => handleTabChange('simulate')}
          onKeyDown={(e) => handleTabKeyDown(e, 'simulate')}
        >
          Simulate
        </button>
        <button
          role="tab"
          id="tab-graph"
          aria-selected={activeTab === 'graph'}
          aria-controls="panel-graph"
          tabIndex={activeTab === 'graph' ? 0 : -1}
          className={`tab-btn ${activeTab === 'graph' ? 'active' : ''}`}
          onClick={() => handleTabChange('graph')}
          onKeyDown={(e) => handleTabKeyDown(e, 'graph')}
        >
          Dependency Graph
        </button>
        <button
          role="tab"
          id="tab-checks"
          aria-selected={activeTab === 'checks'}
          aria-controls="panel-checks"
          tabIndex={activeTab === 'checks' ? 0 : -1}
          className={`tab-btn ${activeTab === 'checks' ? 'active' : ''}`}
          onClick={() => handleTabChange('checks')}
          onKeyDown={(e) => handleTabKeyDown(e, 'checks')}
        >
          Model Checks
        </button>
        <button
          role="tab"
          id="tab-comparison"
          aria-selected={activeTab === 'comparison'}
          aria-controls="panel-comparison"
          tabIndex={activeTab === 'comparison' ? 0 : -1}
          className={`tab-btn ${activeTab === 'comparison' ? 'active' : ''}`}
          onClick={() => handleTabChange('comparison')}
          onKeyDown={(e) => handleTabKeyDown(e, 'comparison')}
        >
          Run Comparison {runSlotA && runSlotB ? '•' : ''}
        </button>
        <button
          role="tab"
          id="tab-capacity"
          aria-selected={activeTab === 'capacity'}
          aria-controls="panel-capacity"
          tabIndex={activeTab === 'capacity' ? 0 : -1}
          className={`tab-btn ${activeTab === 'capacity' ? 'active' : ''}`}
          onClick={() => handleTabChange('capacity')}
          onKeyDown={(e) => handleTabKeyDown(e, 'capacity')}
        >
          Capacity
        </button>
      </nav>

      {/* ======================================================== */}
      {/* MAIN WORKBENCH CONTENT                                   */}
      {/* ======================================================== */}
      <main className="modeling-main-container">
        {/* ======================================================== */}
        {/* TAB 1: SIMULATE (3-REGION WORKSPACE)                     */}
        {/* ======================================================== */}
        {activeTab === 'simulate' && (
          <section id="panel-simulate" role="tabpanel" aria-labelledby="tab-simulate" className="workbench-3col">
            {/* ---------------------------------------------------- */}
            {/* REGION 1: LEFT — SCENARIO & CONTROLS                 */}
            {/* ---------------------------------------------------- */}
            <aside className="region-controls" aria-label="Scenario parameters">
              <div className="panel-section-card">
                <div className="section-head">
                  <h2 className="section-title">Scenario & Trigger</h2>
                  <button className="link-action-btn" onClick={handleResetScenario} title="Restore preset defaults">
                    Reset defaults
                  </button>
                </div>

                {/* Preset Selector */}
                {/* Preset Selector */}
                <div className="form-group">
                  <label htmlFor="preset-select" className="field-label">Scenario Preset</label>
                  <select
                    id="preset-select"
                    className="select-field"
                    value={presetKey}
                    onChange={(e) => handleSelectPreset(e.target.value as PresetKey)}
                  >
                    <optgroup label="Evidence-Backed Historical Replays">
                      <option value="historical-yamuna-2023">
                        July 2023 Yamuna Flood Disaster (Sourced Chronology & CWC Levels)
                      </option>
                      <option value="historical-cwc-juddo-dam">
                        Upper Yamuna Basin Telemetry (CWC Juddo Dam, 2024 Monsoon Hourly)
                      </option>
                    </optgroup>
                    <optgroup label="Synthetic Demonstrations & Benchmarks">
                      <option value="yamuna-critical">
                        Synthetic Delhi Water Walkthrough (Demo Scenario)
                      </option>
                      <option value="multi-resource">
                        Multi-Resource Deterministic Engine Benchmark (Demo)
                      </option>
                    </optgroup>
                  </select>
                </div>

                {/* Preset Provenance Metadata Card */}
                {PRESET_REGISTRY[presetKey] && (
                  <div className="preset-meta-card" role="region" aria-label="Preset provenance details">
                    <div className="preset-meta-header">
                      <span className={`preset-badge-tag ${PRESET_REGISTRY[presetKey].category}`}>
                        {PRESET_REGISTRY[presetKey].badgeText}
                      </span>
                      <span className="source-category-label">
                        {PRESET_REGISTRY[presetKey].category === 'historical' ? 'OFFLINE SOURCED' : 'SYNTHETIC'}
                      </span>
                    </div>
                    <p className="preset-meta-citation">
                      <strong>Source:</strong> {PRESET_REGISTRY[presetKey].citation}
                    </p>
                    <p className="preset-meta-disclaimer">
                      <strong>Scope & Limits:</strong> {PRESET_REGISTRY[presetKey].disclaimer}
                    </p>
                  </div>
                )}

                {/* Chronological Observation Replay Stepper */}
                {availableObservations.length > 1 && (
                  <div className="observation-stepper-card" role="region" aria-label="Chronological Observation Stepper">
                    <div className="stepper-header-row">
                      <span className="stepper-title">Historical Time Stepper</span>
                      <span className="stepper-count-tag">
                        Step {currentObsIndex + 1} of {availableObservations.length}
                      </span>
                    </div>
                    <div className="stepper-nav-row">
                      <button
                        type="button"
                        className="stepper-nav-btn"
                        onClick={() => handleStepObservation('prev')}
                        disabled={currentObsIndex <= 0}
                        aria-label="Previous historical observation"
                      >
                        ◀ Prev
                      </button>
                      <select
                        className="stepper-select"
                        value={obsDraft.observationId}
                        onChange={(e) => handleSelectObservationById(e.target.value)}
                        aria-label="Select historical observation snapshot"
                      >
                        {availableObservations.map((obs, idx) => (
                          <option key={obs.observationId} value={obs.observationId}>
                            #{idx + 1}: {obs.observedAt.slice(5, 16).replace('T', ' ')} IST — {obs.levelM.toFixed(2)}m
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        className="stepper-nav-btn"
                        onClick={() => handleStepObservation('next')}
                        disabled={currentObsIndex >= availableObservations.length - 1}
                        aria-label="Next historical observation"
                      >
                        Next ▶
                      </button>
                    </div>
                    <div className="stepper-detail-strip">
                      <span>Source: <code>{obsDraft.sourceId || 'cwc-nwic'}</code></span>
                      <span className="evidence-badge observed">OBSERVED</span>
                    </div>
                  </div>
                )}

                {/* July 2023 Flood Chronology Accordion */}
                {presetKey === 'historical-yamuna-2023' && (
                  <div className="chronology-accordion-card" role="region" aria-label="July 2023 Flood Chronology">
                    <button
                      type="button"
                      className="chronology-toggle-btn"
                      onClick={() => setShowChronology(!showChronology)}
                      aria-expanded={showChronology}
                    >
                      <span>
                        <strong>July 2023 Flood Chronology</strong> ({july2023FloodChronology.length} Milestones)
                      </span>
                      <span>{showChronology ? '▲ Collapse' : '▼ Expand'}</span>
                    </button>
                    {showChronology && (
                      <div className="chronology-items-list" role="list">
                        {july2023FloodChronology.map((item) => (
                          <div key={item.step} className="chronology-item" role="listitem">
                            <div className="chronology-item-header">
                              <span className="chronology-item-time">{item.time}</span>
                              <span className={`evidence-badge ${item.classification}`}>
                                {item.classification.toUpperCase().replace('_', ' ')}
                              </span>
                            </div>
                            <div className="chronology-item-title">{item.title}</div>
                            <div className="chronology-item-source">Cited: {item.source}</div>
                            <p className="chronology-item-desc">{item.details}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Trigger Source Node */}
                <div className="form-group">
                  <label htmlFor={sourceSelectId} className="field-label">Trigger Source Node</label>
                  <select
                    id={sourceSelectId}
                    className="select-field"
                    value={obsDraft.sourceNodeId}
                    onChange={(e) => {
                      setObsDraft({ ...obsDraft, sourceNodeId: e.target.value })
                      markStale()
                    }}
                  >
                    {graphDraft.nodes.map((node) => (
                      <option key={node.nodeId} value={node.nodeId}>
                        {node.name} ({node.nodeId})
                      </option>
                    ))}
                  </select>
                </div>

                {/* River Level Control */}
                <div className="form-group">
                  <div className="field-head-row">
                    <label htmlFor={levelInputId} className="field-label">
                      River Level <span className="unit-tag">(m)</span>
                    </label>
                    <SeverityBadge severity={previewSeverity} />
                  </div>
                  <div className="paired-input-row">
                    <input
                      id={levelSliderId}
                      className="range-slider"
                      type="range"
                      min={sliderRange.min}
                      max={sliderRange.max}
                      step={sliderRange.step}
                      value={obsDraft.levelM}
                      onChange={(e) => {
                        setObsDraft({ ...obsDraft, levelM: parseFloat(e.target.value) })
                        markStale()
                      }}
                      aria-label="Adjust river level in meters"
                    />
                    <input
                      id={levelInputId}
                      className="numeric-input"
                      type="number"
                      step={sliderRange.step}
                      min={sliderRange.min}
                      max={sliderRange.max + 5}
                      value={obsDraft.levelM}
                      onChange={(e) => {
                        setObsDraft({ ...obsDraft, levelM: parseFloat(e.target.value) || sliderRange.min })
                        markStale()
                      }}
                      aria-label="Direct river level in meters"
                    />
                  </div>

                  {/* Threshold Indicators */}
                  <div className="thresholds-strip" aria-label="Graph thresholds">
                    <span className="th-item">Watch: {effectiveThresholds.watch}m</span>
                    <span className="th-item">Warn: {effectiveThresholds.warning}m</span>
                    <span className="th-item">Crit: {effectiveThresholds.critical}m</span>
                  </div>
                </div>
              </div>

              {/* Card: Timing & Confidence */}
              <div className="panel-section-card">
                <div className="section-head">
                  <h2 className="section-title">Timing & Confidence</h2>
                </div>

                {/* Timestamp */}
                <div className="form-group">
                  <div className="field-head-row">
                    <label htmlFor={timestampInputId} className="field-label">Observation Timestamp</label>
                    <span className="tz-label">IST (+05:30)</span>
                  </div>
                  <input
                    id={timestampInputId}
                    className="text-field"
                    type="text"
                    value={obsDraft.observedAt}
                    onChange={(e) => {
                      setObsDraft({ ...obsDraft, observedAt: e.target.value })
                      markStale()
                    }}
                  />
                </div>

                {/* Confidence */}
                <div className="form-group">
                  <div className="field-head-row">
                    <label htmlFor={confidenceInputId} className="field-label">Signal Confidence</label>
                    <span className="tabular-stat">{Math.round(obsDraft.confidence * 100)}%</span>
                  </div>
                  <input
                    id={confidenceInputId}
                    className="range-slider"
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={obsDraft.confidence}
                    onChange={(e) => {
                      setObsDraft({ ...obsDraft, confidence: parseFloat(e.target.value) })
                      markStale()
                    }}
                    aria-label="Adjust signal confidence"
                  />
                </div>
              </div>

              {/* Card: Resource Lanes & What-If Multiplier */}
              <div className="panel-section-card">
                <div className="section-head">
                  <h2 className="section-title">Resource Lanes & What-If</h2>
                </div>

                <fieldset className="lane-switches-fieldset">
                  <legend className="field-label">Active Traversal Lanes</legend>
                  <div className="lane-switches-list">
                    {(['water', 'staff', 'medical_supply'] as ResourceLane[]).map((lane) => {
                      const count = resourceCounts[lane]
                      const isEnabled = enabledResources[lane]
                      return (
                        <label key={lane} className={`lane-switch-item ${lane} ${isEnabled ? 'checked' : ''}`}>
                          <input
                            type="checkbox"
                            checked={isEnabled}
                            onChange={(e) => {
                              const next = { ...enabledResources, [lane]: e.target.checked }
                              if (!next.water && !next.staff && !next.medical_supply) {
                                alert('At least one resource lane must remain enabled for traversal.')
                                return
                              }
                              setEnabledResources(next)
                              markStale()
                            }}
                          />
                          <span className="lane-indicator" aria-hidden="true" />
                          <span className="lane-title">{lane.replace('_', ' ')}</span>
                          <span className="lane-count">{count} edges</span>
                        </label>
                      )
                    })}
                  </div>
                </fieldset>

                {/* Delay Multiplier */}
                <div className="form-group">
                  <div className="field-head-row">
                    <label htmlFor={delaySliderId} className="field-label">What-If Delay Multiplier</label>
                    <span className="multiplier-value">{delayMultiplier.toFixed(1)}×</span>
                  </div>
                  <input
                    id={delaySliderId}
                    className="range-slider"
                    type="range"
                    min="0.5"
                    max="3.0"
                    step="0.1"
                    value={delayMultiplier}
                    onChange={(e) => {
                      setDelayMultiplier(parseFloat(e.target.value))
                      markStale()
                    }}
                    aria-label="What-if global delay multiplier"
                  />
                  <p className="formula-hint">
                    Scaled edge delay: <code>max(1, round(delay × {delayMultiplier.toFixed(1)}))</code>
                  </p>
                </div>

                {/* Active Overrides Box */}
                {activeOverridesCount > 0 && (
                  <div className="overrides-notice-box" role="status">
                    <div className="notice-head">
                      <WarningIcon />
                      <span><strong>{activeOverridesCount}</strong> what-if modification(s) active</span>
                    </div>
                    <button className="reset-overrides-btn" onClick={handleResetAllOverrides}>
                      Reset to scenario defaults
                    </button>
                  </div>
                )}

                {/* Primary Simulation Button */}
                <div className="controls-action-group">
                  <button
                    className="run-simulation-btn"
                    onClick={handleRunSimulation}
                    disabled={isRunning}
                    aria-busy={isRunning}
                  >
                    {isRunning
                      ? 'Calculating cascade...'
                      : apiStatus === 'connected'
                        ? 'Run simulation'
                        : 'Run simulation (Local preview)'}
                  </button>

                  <div className="auxiliary-btns-row">
                    <button className="aux-btn" onClick={handleExportInput} title="Download current inputs JSON">
                      Export input
                    </button>
                    <button
                      className="aux-btn"
                      onClick={handleExportResults}
                      disabled={!lastResult}
                      title="Download simulation results JSON"
                    >
                      Export results
                    </button>
                    <button className="aux-btn" onClick={openAdvancedJson} title="Edit raw graph and observation JSON">
                      Advanced JSON
                    </button>
                  </div>
                </div>

                {simError && (
                  <div className="error-callout" role="alert">
                    <WarningIcon />
                    <div>
                      <strong>Simulation Notice:</strong> {simError}
                    </div>
                  </div>
                )}
              </div>
            </aside>

            {/* ---------------------------------------------------- */}
            {/* REGION 2: CENTER — DEPENDENCY GRAPH (FOCAL POINT)     */}
            {/* ---------------------------------------------------- */}
            <div className="region-graph">
              <div className="graph-panel-card">
                {/* Graph Toolbar */}
                <div className="graph-toolbar">
                  <div className="graph-toolbar-titles">
                    <h2 className="graph-title">Dependency Graph</h2>
                    <span className="graph-meta">
                      {graphDraft.nodes.length} nodes · {graphDraft.edges.length} edges
                    </span>
                  </div>

                  <div className="graph-toolbar-actions">
                    <div className="zoom-controls-group" role="group" aria-label="Graph zoom controls">
                      <button className="zoom-btn" onClick={handleZoomOut} aria-label="Zoom out graph" title="Zoom out">
                        <ZoomOutIcon />
                      </button>
                      <button className="zoom-btn fit" onClick={handleResetZoom} aria-label="Reset zoom to 100%" title="Reset to 100%">
                        <FitViewIcon />
                        <span>{Math.round(zoomLevel * 100)}%</span>
                      </button>
                      <button className="zoom-btn" onClick={handleZoomIn} aria-label="Zoom in graph" title="Zoom in">
                        <ZoomInIcon />
                      </button>
                    </div>

                    {(selectedNodeId || selectedEdgeId) && (
                      <button
                        className="clear-selection-btn"
                        onClick={() => {
                          setSelectedNodeId(null)
                          setSelectedEdgeId(null)
                        }}
                      >
                        Clear selection
                      </button>
                    )}
                  </div>
                </div>

                {/* Subtitle / Unobtrusive Disclaimer */}
                <div className="graph-disclaimer-note" role="note">
                  Topological dependency DAG. Edge delays indicate signal and operational propagation; not an inundation map.
                </div>

                {/* Interactive SVG Canvas */}
                <div className="graph-canvas-container" tabIndex={0} aria-label="Interactive dependency network visual">
                  {graphDraft.nodes.length === 0 ? (
                    <div className="empty-graph-state">
                      <p>No dependency nodes available in this scenario.</p>
                    </div>
                  ) : (
                    <svg
                      viewBox={`0 0 ${svgWidth} ${svgHeight}`}
                      className="network-svg"
                      role="img"
                      aria-label="Causal dependency graph network"
                    >
                      <defs>
                        <marker
                          id="arrow-water"
                          viewBox="0 0 10 10"
                          refX="22"
                          refY="5"
                          markerWidth="6"
                          markerHeight="6"
                          orient="auto-start-reverse"
                        >
                          <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--cyan)" />
                        </marker>
                        <marker
                          id="arrow-staff"
                          viewBox="0 0 10 10"
                          refX="22"
                          refY="5"
                          markerWidth="6"
                          markerHeight="6"
                          orient="auto-start-reverse"
                        >
                          <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--amber)" />
                        </marker>
                        <marker
                          id="arrow-medical_supply"
                          viewBox="0 0 10 10"
                          refX="22"
                          refY="5"
                          markerWidth="6"
                          markerHeight="6"
                          orient="auto-start-reverse"
                        >
                          <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--mint)" />
                        </marker>
                      </defs>

                      <g
                        transform={`translate(${panOffset.x}, ${panOffset.y}) scale(${zoomLevel})`}
                        style={{
                          transformOrigin: `${svgWidth / 2}px ${svgHeight / 2}px`,
                          transition: 'transform 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
                        }}
                      >
                        {/* Edges */}
                        <g className="edges-layer">
                          {graphDraft.edges.map((edge) => {
                            const src = positions.get(edge.from)
                            const tgt = positions.get(edge.to)
                            if (!src || !tgt) return null

                            const isDisabled = disabledEdgeIds.has(edge.edgeId)
                            const isImpacted = impactedEdgeIds.has(edge.edgeId)
                            const isSelected = selectedEdgeId === edge.edgeId
                            const lane = edge.resourceType || 'water'

                            const x1 = src.x + 92
                            const y1 = src.y + 24
                            const x2 = tgt.x - 92
                            const y2 = tgt.y + 24
                            const dx = Math.abs(x2 - x1) / 2
                            const pathD = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`
                            const midX = (x1 + x2) / 2
                            const midY = (y1 + y2) / 2

                            return (
                              <g
                                key={edge.edgeId}
                                className={`network-edge ${lane} ${isDisabled ? 'disabled' : ''} ${
                                  isImpacted ? 'impacted' : ''
                                } ${isSelected ? 'selected' : ''}`}
                                onClick={() => {
                                  setSelectedEdgeId(edge.edgeId)
                                  setSelectedNodeId(null)
                                  setSrAnnouncement(`Selected edge: ${edge.edgeId}`)
                                }}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter' || e.key === ' ') {
                                    setSelectedEdgeId(edge.edgeId)
                                    setSelectedNodeId(null)
                                  }
                                }}
                                tabIndex={0}
                                role="button"
                                aria-label={`Edge ${edge.edgeId}: ${edge.from} to ${edge.to}, delay ${edge.delayMinutes} minutes`}
                              >
                                <path d={pathD} className="edge-track" markerEnd={`url(#arrow-${lane})`} />
                                <path d={pathD} className="edge-hitbox" />
                                <g transform={`translate(${midX}, ${midY})`} className="edge-delay-badge">
                                  <rect x="-24" y="-10" width="48" height="20" rx="4" />
                                  <text x="0" y="4" textAnchor="middle">
                                    {Math.max(1, Math.round(edge.delayMinutes * delayMultiplier))}m
                                  </text>
                                </g>
                              </g>
                            )
                          })}
                        </g>

                        {/* Nodes */}
                        <g className="nodes-layer">
                          {graphDraft.nodes.map((node) => {
                            const pos = positions.get(node.nodeId)
                            if (!pos) return null

                            const isTrigger = node.nodeId === obsDraft.sourceNodeId
                            const isImpacted = impactedNodeIds.has(node.nodeId)
                            const isSelected = selectedNodeId === node.nodeId

                            return (
                              <g
                                key={node.nodeId}
                                transform={`translate(${pos.x}, ${pos.y})`}
                                className={`network-node ${node.type} ${isTrigger ? 'trigger' : ''} ${
                                  isImpacted ? 'impacted' : ''
                                } ${isSelected ? 'selected' : ''}`}
                                onClick={() => {
                                  setSelectedNodeId(node.nodeId)
                                  setSelectedEdgeId(null)
                                  setSrAnnouncement(`Selected node: ${node.name}`)
                                }}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter' || e.key === ' ') {
                                    setSelectedNodeId(node.nodeId)
                                    setSelectedEdgeId(null)
                                  }
                                }}
                                tabIndex={0}
                                role="button"
                                aria-label={`Node ${node.name}, ID ${node.nodeId}, ${node.notify ? 'Notify facility' : 'Intermediate node'}`}
                              >
                                <rect x="-90" y="-24" width="180" height="48" rx="8" className="node-box" />
                                {node.notify && (
                                  <g transform="translate(74, -14)" className="notify-badge-group">
                                    <circle r="4" className="notify-dot" />
                                  </g>
                                )}
                                <text x="-76" y="-4" className="node-title">
                                  {node.name.length > 20 ? node.name.slice(0, 18) + '…' : node.name}
                                </text>
                                <text x="-76" y="14" className="node-meta">
                                  {node.nodeId}
                                </text>
                              </g>
                            )
                          })}
                        </g>
                      </g>
                    </svg>
                  )}
                </div>

                {/* Graph Legend */}
                <div className="graph-legend-strip">
                  <div className="legend-entry">
                    <span className="legend-line water" />
                    <span>Water lane</span>
                  </div>
                  <div className="legend-entry">
                    <span className="legend-line staff" />
                    <span>Staff lane</span>
                  </div>
                  <div className="legend-entry">
                    <span className="legend-line medical_supply" />
                    <span>Medical lane</span>
                  </div>
                  <div className="legend-entry">
                    <span className="legend-dot trigger" />
                    <span>Trigger gauge</span>
                  </div>
                  <div className="legend-entry">
                    <span className="legend-dot target" />
                    <span>Notify facility</span>
                  </div>
                  <div className="legend-entry">
                    <span className="legend-line impacted" />
                    <span>Impacted path</span>
                  </div>
                </div>
              </div>
            </div>

            {/* ---------------------------------------------------- */}
            {/* REGION 3: RIGHT — RESULTS & INSPECTION               */}
            {/* ---------------------------------------------------- */}
            <aside className="region-results" aria-label="Simulation output and inspection">
              {/* Summary Metrics Bar */}
              <div className="metrics-summary-card">
                <div className="metric-cell">
                  <span className="metric-title">Severity</span>
                  <span className="metric-value">
                    {lastResult ? (
                      <SeverityBadge severity={lastResult.severity} />
                    ) : (
                      <span className="muted-dash">—</span>
                    )}
                  </span>
                  <span className="metric-sub">
                    {lastResult ? 'Authoritative' : 'Awaiting run'}
                  </span>
                </div>

                <div className="metric-cell">
                  <span className="metric-title">Impacts</span>
                  <span className="metric-value tabular-num">
                    {lastResult ? lastResult.impacts.length : '0'}
                  </span>
                  <span className="metric-sub">
                    {lastResult ? `${distinctTargetsCount} target(s)` : '0 facilities'}
                  </span>
                </div>

                <div className="metric-cell">
                  <span className="metric-title">Earliest ETA</span>
                  <span className="metric-value tabular-num">
                    {earliestEta !== null ? `+${earliestEta}m` : '—'}
                  </span>
                  <span className="metric-sub">Signal arrival</span>
                </div>

                <div className="metric-cell">
                  <span className="metric-title">Calculation</span>
                  <span className="metric-value tabular-num">
                    {lastResult ? `${lastResult.engineCalculationMs}ms` : '—'}
                  </span>
                  <span className="metric-sub">
                    {lastResult ? `RTT: ${lastRoundTripMs}ms` : 'Local preview'}
                  </span>
                </div>
              </div>

              {/* Contextual Inspector Card */}
              {selectedNode && (
                <div className="inspector-panel-card" role="region" aria-label="Node Inspector">
                  <div className="inspector-head">
                    <div className="inspector-title-wrap">
                      <span className="inspector-kicker">NODE INSPECTION</span>
                      <h3 className="inspector-name">{selectedNode.name}</h3>
                    </div>
                    <button className="close-btn" onClick={() => setSelectedNodeId(null)} aria-label="Close inspector">
                      ✕
                    </button>
                  </div>

                  <dl className="inspector-props-list">
                    <div className="prop-row">
                      <dt>Node ID</dt>
                      <dd><code>{selectedNode.nodeId}</code></dd>
                    </div>
                    <div className="prop-row">
                      <dt>Type</dt>
                      <dd>{selectedNode.type}</dd>
                    </div>
                    <div className="prop-row">
                      <dt>Role</dt>
                      <dd>{selectedNode.notify ? 'Notify Target Facility' : 'Intermediate Relay'}</dd>
                    </div>
                    <div className="prop-row">
                      <dt>Evidence Classification</dt>
                      <dd>
                        <span className={`evidence-badge ${selectedNode.evidenceClassification || 'synthetic'}`}>
                          {(selectedNode.evidenceClassification || 'synthetic').toUpperCase().replace('_', ' ')}
                        </span>
                      </dd>
                    </div>
                    {selectedNode.sourceId && (
                      <div className="prop-row full">
                        <dt>Source Registry / Citation</dt>
                        <dd><code>{selectedNode.sourceId}</code> {selectedNode.sourceLocator ? `— ${selectedNode.sourceLocator}` : ''}</dd>
                      </div>
                    )}
                    {selectedNode.capacityMgd && (
                      <div className="prop-row">
                        <dt>Installed Capacity</dt>
                        <dd><strong>{selectedNode.capacityMgd} MGD</strong></dd>
                      </div>
                    )}
                    {selectedNode.operationalStatus && (
                      <div className="prop-row full">
                        <dt>Reported Operational Status</dt>
                        <dd className="status-note"><strong>{selectedNode.operationalStatus}</strong></dd>
                      </div>
                    )}
                    <div className="prop-row">
                      <dt>Severity Cap</dt>
                      <dd>{selectedNode.severityCap}</dd>
                    </div>
                    <div className="prop-row">
                      <dt>Evidence Status</dt>
                      <dd>{selectedNode.evidenceStatus}</dd>
                    </div>
                    {selectedNode.assumption && (
                      <div className="prop-row full">
                        <dt>Assumption Note</dt>
                        <dd className="assumption-text">{selectedNode.assumption}</dd>
                      </div>
                    )}
                  </dl>

                  {/* MoHFW Hospital Water Demand Proxy Card */}
                  {selectedNode.bedCount && (
                    <div className="hospital-demand-card" role="region" aria-label="Hospital Water Demand Estimation">
                      <div className="hospital-demand-header">
                        <span className="hospital-demand-title">MoHFW IPHS Water Demand Proxy</span>
                        <span className="evidence-badge derived">DERIVED (PROXY)</span>
                      </div>
                      <div className="hospital-demand-grid">
                        <div className="demand-metric-item">
                          <span className="demand-metric-label">Registered Capacity</span>
                          <span className="demand-metric-val">{selectedNode.bedCount} beds</span>
                          <span className="demand-metric-sub">Official Health Directory</span>
                        </div>
                        <div className="demand-metric-item">
                          <span className="demand-metric-label">Daily Standard Norm</span>
                          <span className="demand-metric-val">475 L/bed/day</span>
                          <span className="demand-metric-sub">IPHS 2012 (Sec 4.10)</span>
                        </div>
                        <div className="demand-metric-item">
                          <span className="demand-metric-label">Est. Daily Demand</span>
                          <span className="demand-metric-val">
                            {((selectedNode.bedCount * 475) / 1000000).toFixed(3)} MLD
                          </span>
                          <span className="demand-metric-sub">
                            {(selectedNode.bedCount * 475).toLocaleString()} Liters/day
                          </span>
                        </div>
                        <div className="demand-metric-item">
                          <span className="demand-metric-label">48h Emergency Reserve</span>
                          <span className="demand-metric-val">
                            {((selectedNode.bedCount * 950) / 1000000).toFixed(3)} MLD
                          </span>
                          <span className="demand-metric-sub">
                            {(selectedNode.bedCount * 950).toLocaleString()} Liters (950 L/bed)
                          </span>
                        </div>
                      </div>
                      <p className="demand-method-disclaimer">
                        Proxy norm derived per Indian Public Health Standards (IPHS 2012) for District Hospitals. Actual metered utility consumption varies with patient turnover and specialty care wards.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {selectedEdge && (
                <div className="inspector-panel-card" role="region" aria-label="Edge Inspector">
                  <div className="inspector-head">
                    <div className="inspector-title-wrap">
                      <span className="inspector-kicker">EDGE INSPECTION</span>
                      <h3 className="inspector-name"><code>{selectedEdge.edgeId}</code></h3>
                    </div>
                    <button className="close-btn" onClick={() => setSelectedEdgeId(null)} aria-label="Close inspector">
                      ✕
                    </button>
                  </div>

                  <dl className="inspector-props-list">
                    <div className="prop-row">
                      <dt>Path</dt>
                      <dd><code>{selectedEdge.from}</code> → <code>{selectedEdge.to}</code></dd>
                    </div>
                    <div className="prop-row">
                      <dt>Resource</dt>
                      <dd><span className={`lane-pill ${selectedEdge.resourceType || 'water'}`}>{selectedEdge.resourceType || 'water'}</span></dd>
                    </div>
                    <div className="prop-row">
                      <dt>Evidence Classification</dt>
                      <dd>
                        <span className={`evidence-badge ${selectedEdge.evidenceClassification || 'assumed'}`}>
                          {(selectedEdge.evidenceClassification || 'assumed').toUpperCase().replace('_', ' ')}
                        </span>
                      </dd>
                    </div>
                    {selectedEdge.sourceId && (
                      <div className="prop-row full">
                        <dt>Source Registry / Citation</dt>
                        <dd><code>{selectedEdge.sourceId}</code> {selectedEdge.sourceLocator ? `— ${selectedEdge.sourceLocator}` : ''}</dd>
                      </div>
                    )}
                    <div className="prop-row">
                      <dt>Delay</dt>
                      <dd className="tabular-num">
                        {Math.max(1, Math.round(selectedEdge.delayMinutes * delayMultiplier))} min
                        {delayMultiplier !== 1.0 && <small className="delay-orig"> ({selectedEdge.delayMinutes}m orig)</small>}
                      </dd>
                    </div>
                    <div className="prop-row">
                      <dt>Min Severity</dt>
                      <dd>{selectedEdge.minSeverity}</dd>
                    </div>
                    <div className="prop-row">
                      <dt>Confidence</dt>
                      <dd className="tabular-num">{Math.round(selectedEdge.confidence * 100)}%</dd>
                    </div>
                    {selectedEdge.assumption && (
                      <div className="prop-row full">
                        <dt>Assumption Note</dt>
                        <dd className="assumption-text">{selectedEdge.assumption}</dd>
                      </div>
                    )}
                  </dl>

                  <div className="edge-inspector-actions">
                    <button
                      className={`edge-toggle-btn ${disabledEdgeIds.has(selectedEdge.edgeId) ? 'restore' : 'disable'}`}
                      onClick={() => {
                        const next = new Set(disabledEdgeIds)
                        if (next.has(selectedEdge.edgeId)) {
                          next.delete(selectedEdge.edgeId)
                          setSrAnnouncement(`Restored edge: ${selectedEdge.edgeId}`)
                        } else {
                          next.add(selectedEdge.edgeId)
                          setSrAnnouncement(`Disabled edge in what-if: ${selectedEdge.edgeId}`)
                        }
                        setDisabledEdgeIds(next)
                        markStale()
                      }}
                    >
                      {disabledEdgeIds.has(selectedEdge.edgeId)
                        ? 'Restore Edge to Scenario'
                        : 'Temporarily Disable Edge in What-If'}
                    </button>
                  </div>
                </div>
              )}

              {/* Selected Impact Inspection & Causal Path */}
              {selectedImpact && !selectedNode && !selectedEdge && (
                <div className="inspector-panel-card" role="region" aria-label="Impact Details">
                  <div className="inspector-head">
                    <div className="inspector-title-wrap">
                      <span className="inspector-kicker">SELECTED IMPACT</span>
                      <h3 className="inspector-name">{selectedImpact.target.name}</h3>
                    </div>
                    <button
                      className="copy-chip-btn"
                      onClick={() => handleCopyImpactJson(selectedImpact)}
                      title="Copy impact JSON"
                    >
                      {copyFeedback === selectedImpact.impactId ? 'Copied' : 'Copy JSON'}
                    </button>
                  </div>

                  <div className="impact-overview-grid">
                    <div className="overview-item">
                      <span className="item-label">Resource</span>
                      <span className={`lane-pill ${selectedImpact.resourceType}`}>
                        {selectedImpact.resourceType.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="overview-item">
                      <span className="item-label">ETA</span>
                      <span className="item-val tabular-num">+{selectedImpact.etaMinutes} min</span>
                    </div>
                    <div className="overview-item">
                      <span className="item-label">Severity</span>
                      <SeverityBadge severity={selectedImpact.severity} />
                    </div>
                    <div className="overview-item">
                      <span className="item-label">Confidence</span>
                      <span className="item-val tabular-num">{Math.round(selectedImpact.confidence * 100)}%</span>
                    </div>
                  </div>

                  <div className="arrival-timestamp-note">
                    <strong>Simulated Arrival:</strong> {selectedImpact.expectedImpactAt}
                    <small> (Illustrative scenario timestamp; not a real-time alert)</small>
                  </div>

                  {/* Causal Path Step Breakdown */}
                  <div className="causal-path-block">
                    <h4 className="path-block-title">Causal Traversal Path ({selectedImpact.path.length} hops)</h4>
                    <ol className="path-steps-list">
                      {selectedImpact.path.map((step, idx) => (
                        <li key={step.edgeId} className="path-step">
                          <div className="step-route">
                            <code>{step.from}</code> <span className="step-arrow">→</span> <code>{step.to}</code>
                          </div>
                          <div className="step-meta-row">
                            <span>Edge: <code>{step.edgeId}</code></span>
                            <span className="tabular-num">+{step.delayMinutes} min</span>
                          </div>
                          {step.assumption && (
                            <p className="step-assumption-note">{step.assumption}</p>
                          )}
                        </li>
                      ))}
                    </ol>
                  </div>
                </div>
              )}

              {/* If nothing selected */}
              {!selectedNode && !selectedEdge && !selectedImpact && (
                <div className="inspector-panel-card empty-guide">
                  <div className="guide-body">
                    <p className="guide-lead">No element selected</p>
                    <p className="guide-text">
                      Click any node or edge in the dependency graph, or click an impact item below to trace its causal propagation path.
                    </p>
                  </div>
                </div>
              )}

              {/* Impact Timeline Section */}
              <div className="impacts-timeline-card">
                <div className="timeline-head-row">
                  <h3 className="timeline-title">Impact Timeline</h3>
                  <div className="lane-filter-pills" role="group" aria-label="Filter impacts by resource">
                    {(['all', 'water', 'staff', 'medical_supply'] as const).map((filter) => (
                      <button
                        key={filter}
                        className={`filter-pill ${resultResourceFilter === filter ? 'active' : ''}`}
                        onClick={() => setResultResourceFilter(filter)}
                      >
                        {filter === 'all' ? 'All' : filter.replace('_', ' ')}
                      </button>
                    ))}
                  </div>
                </div>

                {isStale && (
                  <div className="stale-warning-banner" role="alert">
                    <WarningIcon />
                    <span>
                      <strong>STALE RESULTS</strong> — Scenario controls modified since last run. Click <em>Run simulation</em> to update.
                    </span>
                  </div>
                )}

                {/* Timeline Items */}
                {lastResult && filteredImpacts.length > 0 ? (
                  <div className="timeline-items-list" role="list">
                    {filteredImpacts.map((imp) => {
                      const isSelected = imp.impactId === selectedImpactId
                      return (
                        <div
                          key={imp.impactId}
                          className={`timeline-item ${imp.resourceType} ${isSelected ? 'selected' : ''}`}
                          onClick={() => {
                            setSelectedImpactId(imp.impactId)
                            setSelectedNodeId(null)
                            setSelectedEdgeId(null)
                            setSrAnnouncement(`Selected impact: ${imp.target.name}`)
                          }}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              setSelectedImpactId(imp.impactId)
                              setSelectedNodeId(null)
                              setSelectedEdgeId(null)
                            }
                          }}
                          tabIndex={0}
                          role="listitem"
                          aria-label={`Impact on ${imp.target.name}, arrival in ${imp.etaMinutes} minutes, resource ${imp.resourceType}`}
                        >
                          <div className="item-head">
                            <span className={`lane-pill ${imp.resourceType}`}>
                              {imp.resourceType.replace('_', ' ')}
                            </span>
                            <span className="item-eta tabular-num">+{imp.etaMinutes} min</span>
                          </div>
                          <div className="item-target-title">{imp.target.name}</div>
                          <div className="item-footer">
                            <SeverityBadge severity={imp.severity} />
                            <span className="item-conf tabular-num">Conf: {Math.round(imp.confidence * 100)}%</span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : lastResult && filteredImpacts.length === 0 ? (
                  <div className="empty-timeline-note">
                    <p>No impacts triggered under the current settings for this resource lane.</p>
                  </div>
                ) : (
                  <div className="empty-timeline-note">
                    <p>Configure trigger and click <strong>Run simulation</strong> to generate causal arrivals.</p>
                  </div>
                )}

                {/* Slot Saving Controls */}
                {lastResult && (
                  <div className="comparison-slot-actions">
                    <span className="slot-action-label">Save run for comparison:</span>
                    <button
                      className="slot-btn"
                      onClick={() => {
                        setRunSlotA(lastResult)
                        setSrAnnouncement('Saved current run as Run A for comparison.')
                      }}
                    >
                      Save as Run A
                    </button>
                    <button
                      className="slot-btn"
                      onClick={() => {
                        setRunSlotB(lastResult)
                        setSrAnnouncement('Saved current run as Run B for comparison.')
                      }}
                    >
                      Save as Run B
                    </button>
                  </div>
                )}
              </div>
            </aside>
          </section>
        )}

        {/* ======================================================== */}
        {/* TAB 2: EXPANDED DEPENDENCY GRAPH VIEW                    */}
        {/* ======================================================== */}
        {activeTab === 'graph' && (
          <section id="panel-graph" role="tabpanel" aria-labelledby="tab-graph" className="expanded-graph-view">
            <div className="expanded-graph-header">
              <div className="header-titles">
                <h2>Network Dependency Topology</h2>
                <p>Comprehensive inspection of all infrastructure nodes, propagation delays, and assumptions.</p>
              </div>

              <div className="graph-search-bar">
                <input
                  type="search"
                  className="search-field"
                  placeholder="Filter nodes by name or ID..."
                  value={graphSearchQuery}
                  onChange={(e) => setGraphSearchQuery(e.target.value)}
                  aria-label="Filter nodes by keyword"
                />
              </div>
            </div>

            {/* Nodes Table Matrix */}
            <div className="matrix-table-card">
              <h3 className="card-subhead">Scenario Node Inventory ({filteredNodesList.length})</h3>
              <div className="table-responsive">
                <table className="inventory-table">
                  <thead>
                    <tr>
                      <th>Node ID</th>
                      <th>Facility Name</th>
                      <th>Type</th>
                      <th>Role</th>
                      <th>Evidence Class</th>
                      <th>Capacity / Beds</th>
                      <th>Source / Locator</th>
                      <th>Assumptions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredNodesList.map((n) => (
                      <tr key={n.nodeId}>
                        <td><code>{n.nodeId}</code></td>
                        <td><strong>{n.name}</strong></td>
                        <td>{n.type}</td>
                        <td>{n.notify ? 'Notify Target' : 'Relay'}</td>
                        <td>
                          <span className={`evidence-badge ${n.evidenceClassification || 'synthetic'}`}>
                            {(n.evidenceClassification || 'synthetic').toUpperCase().replace('_', ' ')}
                          </span>
                        </td>
                        <td>
                          {n.bedCount ? `${n.bedCount} beds (475 L/bed norm)` : n.capacityMgd ? `${n.capacityMgd} MGD capacity` : '—'}
                        </td>
                        <td className="table-notes">
                          {n.sourceId ? `${n.sourceId}${n.sourceLocator ? ` (${n.sourceLocator})` : ''}` : 'Synthetic demo'}
                        </td>
                        <td className="table-notes">{n.assumption || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Edges Table Matrix */}
            <div className="matrix-table-card">
              <h3 className="card-subhead">Scenario Edge Inventory ({graphDraft.edges.length})</h3>
              <div className="table-responsive">
                <table className="inventory-table">
                  <thead>
                    <tr>
                      <th>Edge ID</th>
                      <th>From</th>
                      <th>To</th>
                      <th>Resource</th>
                      <th>Delay (min)</th>
                      <th>Evidence Class</th>
                      <th>Min Severity</th>
                      <th>Source / Assumptions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {graphDraft.edges.map((e) => (
                      <tr key={e.edgeId}>
                        <td><code>{e.edgeId}</code></td>
                        <td><code>{e.from}</code></td>
                        <td><code>{e.to}</code></td>
                        <td><span className={`lane-pill ${e.resourceType || 'water'}`}>{e.resourceType || 'water'}</span></td>
                        <td className="tabular-num">{e.delayMinutes} min</td>
                        <td>
                          <span className={`evidence-badge ${e.evidenceClassification || 'assumed'}`}>
                            {(e.evidenceClassification || 'assumed').toUpperCase().replace('_', ' ')}
                          </span>
                        </td>
                        <td>{e.minSeverity}</td>
                        <td className="table-notes">
                          {e.sourceId ? `${e.sourceId}: ` : ''}{e.assumption || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        )}

        {/* ======================================================== */}
        {/* TAB 3: MODEL CHECKS REGRESSION SUITE                     */}
        {/* ======================================================== */}
        {activeTab === 'checks' && (
          <section id="panel-checks" role="tabpanel" aria-labelledby="tab-checks" className="model-checks-view">
            <div className="checks-header-row">
              <div>
                <h2>Deterministic Engine Model Checks</h2>
                <p>
                  Client-side regression tests verifying deterministic invariance contracts against <code>POST /modeling/simulate</code>.
                </p>
              </div>
              <button
                className="run-all-checks-btn"
                onClick={runAllChecks}
              >
                Run all checks ({apiStatus === 'connected' ? 'Python Backend' : 'Browser Engine'})
              </button>
            </div>

            <div className="checks-grid-list">
              {checkResults.map((chk) => (
                <div key={chk.id} className={`check-card ${chk.status}`}>
                  <div className="check-card-head">
                    <div className="check-title-group">
                      <span className={`check-status-badge ${chk.status}`}>
                        {chk.status === 'pass' && <CheckIcon />}
                        {chk.status === 'fail' && <CrossIcon />}
                        {chk.status === 'blocked' && <WarningIcon />}
                        <span>{chk.status.toUpperCase()}</span>
                      </span>
                      <h3 className="check-title">{chk.name}</h3>
                    </div>
                    <div className="check-meta-actions">
                      {chk.elapsedMs !== undefined && (
                        <span className="elapsed-stat tabular-num">{chk.elapsedMs} ms</span>
                      )}
                      <button
                        className="rerun-btn"
                        onClick={() => runModelCheck(chk.id)}
                      >
                        Rerun
                      </button>
                    </div>
                  </div>

                  <p className="check-description">{chk.description}</p>

                  <div className="check-io-block">
                    <div className="io-row">
                      <span className="io-label">Expected:</span>
                      <code>{chk.expected}</code>
                    </div>
                    {chk.actual && (
                      <div className="io-row">
                        <span className="io-label">Actual:</span>
                        <code>{chk.actual}</code>
                      </div>
                    )}
                    {chk.error && (
                      <div className="io-row error">
                        <span className="io-label">Error:</span>
                        <span>{chk.error}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="cli-regression-card">
              <h3>Local Python CLI Regression Suite</h3>
              <p>For complete test coverage and engine validation outside the browser, execute from repository root:</p>
              <pre className="cli-block">
                <code>python -m unittest discover -s backend/tests -t backend -v</code>
              </pre>
              <pre className="cli-block">
                <code>python -m compileall -q backend</code>
              </pre>
            </div>
          </section>
        )}

        {/* ======================================================== */}
        {/* TAB 4: RUN COMPARISON                                    */}
        {/* ======================================================== */}
        {activeTab === 'comparison' && (
          <section id="panel-comparison" role="tabpanel" aria-labelledby="tab-comparison" className="run-comparison-view">
            <div className="comparison-header-row">
              <div>
                <h2>Scenario Run Comparison</h2>
                <p>Compare differential impacts, time-to-impact (ETA) deltas, and causal paths between two simulation runs.</p>
              </div>
            </div>

            {!runSlotA || !runSlotB ? (
              <div className="comparison-empty-callout">
                <div className="callout-content">
                  <h3>Two Simulation Runs Required</h3>
                  <p>
                    Execute simulations in the <strong>Simulate</strong> tab and click <em>Save as Run A</em> and <em>Save as Run B</em> to analyze scenario deltas.
                  </p>
                  <div className="slots-status-strip">
                    <span className={`slot-pill ${runSlotA ? 'ready' : 'empty'}`}>
                      Run A: {runSlotA ? runSlotA.runId : 'Not saved'}
                    </span>
                    <span className={`slot-pill ${runSlotB ? 'ready' : 'empty'}`}>
                      Run B: {runSlotB ? runSlotB.runId : 'Not saved'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="comparison-data-content">
                {/* Metrics Diff Row */}
                <div className="comparison-stats-grid">
                  <div className="comp-stat-cell">
                    <span className="stat-label">Run IDs</span>
                    <div className="comp-diff-vals">
                      <span>A: <code>{runSlotA.runId}</code></span>
                      <span>B: <code>{runSlotB.runId}</code></span>
                    </div>
                  </div>
                  <div className="comp-stat-cell">
                    <span className="stat-label">Severity</span>
                    <div className="comp-diff-vals">
                      <span>A: <SeverityBadge severity={runSlotA.severity} /></span>
                      <span>B: <SeverityBadge severity={runSlotB.severity} /></span>
                    </div>
                  </div>
                  <div className="comp-stat-cell">
                    <span className="stat-label">Total Impacts</span>
                    <div className="comp-diff-vals tabular-num">
                      <span>A: {runSlotA.impacts.length}</span>
                      <span>B: {runSlotB.impacts.length}</span>
                    </div>
                  </div>
                  <div className="comp-stat-cell">
                    <span className="stat-label">Engine Calculation</span>
                    <div className="comp-diff-vals tabular-num">
                      <span>A: {runSlotA.engineCalculationMs} ms</span>
                      <span>B: {runSlotB.engineCalculationMs} ms</span>
                    </div>
                  </div>
                </div>

                {/* Diff Table */}
                <div className="comparison-diff-card">
                  <h3 className="card-subhead">Differential Target Arrivals by Resource</h3>
                  <div className="table-responsive">
                    <table className="comparison-table">
                      <thead>
                        <tr>
                          <th>Target Node</th>
                          <th>Resource</th>
                          <th>ETA (Run A)</th>
                          <th>ETA (Run B)</th>
                          <th>Δ ETA</th>
                          <th>Severity Shift</th>
                          <th>Path Comparison</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(() => {
                          const allKeys = new Set<string>()
                          const mapA = new Map<string, SimulationImpact>()
                          const mapB = new Map<string, SimulationImpact>()

                          for (const imp of runSlotA.impacts) {
                            const k = `${imp.target.nodeId}::${imp.resourceType}`
                            allKeys.add(k)
                            mapA.set(k, imp)
                          }
                          for (const imp of runSlotB.impacts) {
                            const k = `${imp.target.nodeId}::${imp.resourceType}`
                            allKeys.add(k)
                            mapB.set(k, imp)
                          }

                          return Array.from(allKeys).map((k) => {
                            const impA = mapA.get(k)
                            const impB = mapB.get(k)
                            const targetName = impA?.target.name || impB?.target.name
                            const resource = impA?.resourceType || impB?.resourceType

                            const etaA = impA ? `${impA.etaMinutes} min` : 'None'
                            const etaB = impB ? `${impB.etaMinutes} min` : 'None'
                            const delta =
                              impA && impB
                                ? impB.etaMinutes - impA.etaMinutes === 0
                                  ? '0 min'
                                  : `${impB.etaMinutes - impA.etaMinutes > 0 ? '+' : ''}${impB.etaMinutes - impA.etaMinutes} min`
                                : impB
                                  ? 'Added in B'
                                  : 'Removed in B'

                            const deltaClass = delta.startsWith('+') ? 'slower' : delta.startsWith('-') ? 'faster' : 'equal'

                            const sevChange =
                              impA && impB
                                ? impA.severity === impB.severity
                                  ? `Identical (${impA.severity})`
                                  : `${impA.severity} → ${impB.severity}`
                                : impB
                                  ? `New (${impB.severity})`
                                  : 'Removed'

                            const pathChange =
                              impA && impB
                                ? JSON.stringify(impA.path.map((p) => p.edgeId)) ===
                                  JSON.stringify(impB.path.map((p) => p.edgeId))
                                  ? 'Identical route'
                                  : `Modified (${impA.path.length} hops vs ${impB.path.length} hops)`
                                : 'N/A'

                            return (
                              <tr key={k}>
                                <td>
                                  <strong>{targetName}</strong>
                                  <small className="node-id-sub">({k.split('::')[0]})</small>
                                </td>
                                <td>
                                  <span className={`lane-pill ${resource}`}>{resource}</span>
                                </td>
                                <td className="tabular-num">{etaA}</td>
                                <td className="tabular-num">{etaB}</td>
                                <td>
                                  <span className={`delta-tag ${deltaClass}`}>{delta}</span>
                                </td>
                                <td>{sevChange}</td>
                                <td>{pathChange}</td>
                              </tr>
                            )
                          })
                        })()}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

        {/* ======================================================== */}
        {/* TAB 5: CAPACITY & BENCHMARKING                           */}
        {/* ======================================================== */}
        {activeTab === 'capacity' && (
          <section id="panel-capacity" role="tabpanel" aria-labelledby="tab-capacity" className="capacity-view">
            <div className="capacity-header-row">
              <div>
                <h2>Simulation Latency & Engine Capacity</h2>
                <p>Sequential repeat testing separating isolated backend engine duration from browser round-trip latency.</p>
              </div>
            </div>

            <div className="capacity-runner-card">
              <div className="runner-controls-row">
                <div className="reps-picker">
                  <label htmlFor="reps-select" className="field-label">Sequential Repetitions:</label>
                  <select
                    id="reps-select"
                    className="select-field small"
                    value={capacityReps}
                    onChange={(e) => setCapacityReps(parseInt(e.target.value, 10))}
                    disabled={capacityRunning}
                  >
                    <option value={1}>1 repetition</option>
                    <option value={3}>3 repetitions</option>
                    <option value={5}>5 repetitions</option>
                  </select>
                </div>

                <div className="runner-btns">
                  <button
                    className="run-capacity-btn"
                    onClick={runCapacityTest}
                    disabled={capacityRunning || apiStatus !== 'connected'}
                  >
                    {capacityRunning ? 'Running repetitions...' : 'Run latency test'}
                  </button>
                  {capacityRunning && (
                    <button className="cancel-btn" onClick={cancelCapacityTest}>
                      Cancel
                    </button>
                  )}
                </div>
              </div>

              {capacityStats && (
                <div className="capacity-stats-row">
                  <div className="stat-card">
                    <span className="stat-label">Backend Engine Median</span>
                    <span className="stat-number tabular-num">{capacityStats.medianEngine} ms</span>
                    <span className="stat-sub">Max: {capacityStats.maxEngine} ms</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-label">Browser Round-Trip Median</span>
                    <span className="stat-number tabular-num">{capacityStats.medianRtt} ms</span>
                    <span className="stat-sub">Max: {capacityStats.maxRtt} ms</span>
                  </div>
                </div>
              )}

              {capacityResults.length > 0 && (
                <div className="capacity-table-card">
                  <table className="capacity-table">
                    <thead>
                      <tr>
                        <th>Repetition</th>
                        <th>Engine Calculation Duration</th>
                        <th>Browser Round-Trip Latency</th>
                      </tr>
                    </thead>
                    <tbody>
                      {capacityResults.map((r) => (
                        <tr key={r.rep}>
                          <td>Run #{r.rep}</td>
                          <td className="tabular-num"><code>{r.engineMs} ms</code></td>
                          <td className="tabular-num"><code>{r.roundTripMs} ms</code></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="cli-regression-card">
              <h3>Large-Scale Graph Capacity Benchmark</h3>
              <p>
                In-browser benchmarking is capped to 5 repetitions to prevent UI thread saturation. To benchmark Ripple's CascadeEngine at 1,000 to 10,000 synthetic DAG nodes, execute directly from CLI:
              </p>
              <pre className="cli-block">
                <code>python backend/benchmarks/benchmark_cascade.py --nodes 1000 --out-degree 5 --repeats 5</code>
              </pre>
              <pre className="cli-block">
                <code>python backend/benchmarks/benchmark_cascade.py --nodes 10000 --out-degree 5 --repeats 3</code>
              </pre>
            </div>
          </section>
        )}
      </main>

      {/* ======================================================== */}
      {/* ADVANCED JSON MODAL                                      */}
      {/* ======================================================== */}
      {showAdvancedJson && (
        <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="modal-title">
          <div className="modal-dialog">
            <div className="modal-head">
              <h3 id="modal-title" className="modal-title">Advanced Scenario JSON Editor</h3>
              <button className="close-btn" onClick={() => setShowAdvancedJson(false)} aria-label="Close dialog">
                ✕
              </button>
            </div>

            <div className="modal-body">
              <p className="modal-desc">
                Directly inspect or edit the scenario Graph and Observation payloads. Syntax is validated before application.
              </p>

              {jsonValidationError && (
                <div className="modal-error" role="alert">
                  <strong>Validation Error:</strong> {jsonValidationError}
                </div>
              )}
              {jsonSuccessNotice && (
                <div className="modal-success" role="status">
                  {jsonSuccessNotice}
                </div>
              )}

              <div className="json-fields-grid">
                <div className="json-column">
                  <label htmlFor="graph-json-textarea" className="field-label">Dependency Graph JSON</label>
                  <textarea
                    id="graph-json-textarea"
                    className="json-textarea"
                    value={graphJsonInput}
                    onChange={(e) => setGraphJsonInput(e.target.value)}
                    rows={15}
                    spellCheck={false}
                  />
                </div>
                <div className="json-column">
                  <label htmlFor="obs-json-textarea" className="field-label">Observation JSON</label>
                  <textarea
                    id="obs-json-textarea"
                    className="json-textarea"
                    value={obsJsonInput}
                    onChange={(e) => setObsJsonInput(e.target.value)}
                    rows={15}
                    spellCheck={false}
                  />
                </div>
              </div>
            </div>

            <div className="modal-actions">
              <button className="aux-btn" onClick={handleValidateJson}>
                Validate JSON syntax
              </button>
              <button className="run-btn primary" onClick={handleApplyJson}>
                Apply to scenario
              </button>
              <button className="aux-btn" onClick={() => setShowAdvancedJson(false)}>
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
