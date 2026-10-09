import { useEffect, useMemo, useState } from 'react'
import { impacts, levelPoints, scenarioSteps, type Severity } from './data/scenario'

const severityLabel: Record<Severity, string> = {
  stable: 'Stable',
  watch: 'Watch',
  warning: 'Warning',
  critical: 'Critical',
}

function ArrowIcon({ down = false }: { down?: boolean }) {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d={down ? 'M10 3v13M5 11l5 5 5-5' : 'M4 10h12M11 5l5 5-5 5'} />
    </svg>
  )
}

function PlayIcon({ pause = false }: { pause?: boolean }) {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      {pause ? <path d="M6 4v12M14 4v12" /> : <path className="fill" d="m7 4 9 6-9 6V4Z" />}
    </svg>
  )
}

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

function StatusDot({ severity }: { severity: Severity }) {
  return <span className={`status-dot ${severity}`} aria-hidden="true" />
}

function SectionHeading({ number, label, title, copy }: { number: string; label: string; title: React.ReactNode; copy: string }) {
  return (
    <div className="section-heading">
      <div className="section-kicker">
        <span>{number}</span>
        <span>{label}</span>
      </div>
      <div className="section-title-wrap">
        <h2>{title}</h2>
        <p>{copy}</p>
      </div>
    </div>
  )
}

function Hydrograph({ step }: { step: number }) {
  const points = levelPoints.map((value, index) => {
    const x = 22 + index * 72
    const y = 156 - ((value - 203.8) / 2.6) * 118
    return `${x},${y}`
  }).join(' ')
  const cursorX = 22 + Math.min(step + 1, 6) * 72

  return (
    <svg className="hydrograph" viewBox="0 0 480 180" role="img" aria-label="Yamuna water level replay chart">
      <defs>
        <linearGradient id="chartFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--cyan)" stopOpacity=".28" />
          <stop offset="1" stopColor="var(--cyan)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <g className="chart-grid">
        <path d="M22 26H458M22 70H458M22 114H458M22 158H458" />
      </g>
      <path className="threshold-line" d="M22 83H458" />
      <text className="threshold-label" x="454" y="76">WARNING 205.33 M</text>
      <polygon points={`${points} 454,158 22,158`} fill="url(#chartFill)" />
      <polyline className="level-line" points={points} />
      <line className="chart-cursor" x1={cursorX} y1="20" x2={cursorX} y2="160" />
      <circle className="cursor-point" cx={cursorX} cy={156 - ((levelPoints[Math.min(step + 1, 6)] - 203.8) / 2.6) * 118} r="5" />
      <text className="axis-label" x="22" y="175">05:00</text>
      <text className="axis-label" x="228" y="175">06:30</text>
      <text className="axis-label" x="424" y="175">08:20</text>
    </svg>
  )
}

const graphNodes = [
  { id: 'gauge', x: 80, y: 206, label: 'Yamuna', meta: 'GAUGE 01', kind: 'source' },
  { id: 'wazirabad', x: 288, y: 124, label: 'Wazirabad', meta: 'WTP 01', kind: 'plant' },
  { id: 'chandrawal', x: 288, y: 286, label: 'Chandrawal', meta: 'WTP 02', kind: 'plant' },
  { id: 'north-zone', x: 505, y: 124, label: 'North Zone', meta: 'SUPPLY 04', kind: 'zone' },
  { id: 'central-zone', x: 505, y: 286, label: 'Central Zone', meta: 'SUPPLY 07', kind: 'zone' },
  { id: 'hospital-a', x: 728, y: 84, label: 'Hospital', meta: 'CRITICAL 01', kind: 'critical' },
  { id: 'shelter-a', x: 728, y: 170, label: 'Shelter', meta: 'SERVICE 04', kind: 'service' },
  { id: 'hospital-b', x: 728, y: 286, label: 'Clinic', meta: 'CRITICAL 02', kind: 'critical' },
]

const graphEdges = [
  ['gauge', 'wazirabad'], ['gauge', 'chandrawal'], ['wazirabad', 'north-zone'], ['chandrawal', 'central-zone'],
  ['north-zone', 'hospital-a'], ['north-zone', 'shelter-a'], ['central-zone', 'hospital-b'],
]

function CascadeGraph({ activeNodes, selected, onSelect }: { activeNodes: string[]; selected: string; onSelect: (id: string) => void }) {
  const byId = Object.fromEntries(graphNodes.map((node) => [node.id, node]))
  return (
    <svg className="cascade-graph" viewBox="0 0 820 390" role="img" aria-label="Dependency cascade from river gauge to critical facilities">
      <defs>
        <filter id="nodeGlow" x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation="7" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      <g className="graph-grid">
        <path d="M20 40H800M20 120H800M20 200H800M20 280H800M20 360H800" />
        <path d="M80 18V372M288 18V372M505 18V372M728 18V372" />
      </g>
      {graphEdges.map(([from, to]) => {
        const a = byId[from]
        const b = byId[to]
        const active = activeNodes.includes(from) && activeNodes.includes(to)
        return <path key={`${from}-${to}`} className={`graph-edge ${active ? 'active' : ''}`} d={`M${a.x + 27} ${a.y} C${a.x + 100} ${a.y}, ${b.x - 100} ${b.y}, ${b.x - 27} ${b.y}`} />
      })}
      {graphNodes.map((node) => {
        const active = activeNodes.includes(node.id)
        const isSelected = selected === node.id
        return (
          <g
            key={node.id}
            className={`graph-node ${node.kind} ${active ? 'active' : ''} ${isSelected ? 'selected' : ''}`}
            onClick={() => onSelect(node.id)}
            role="button"
            tabIndex={0}
            aria-label={`${node.label}, ${node.meta}`}
            onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') onSelect(node.id) }}
          >
            {active && <circle className="node-pulse" cx={node.x} cy={node.y} r="34" />}
            <circle className="node-shell" cx={node.x} cy={node.y} r="26" filter={active ? 'url(#nodeGlow)' : undefined} />
            <circle className="node-core" cx={node.x} cy={node.y} r="7" />
            <text className="node-label" x={node.x} y={node.y + 48} textAnchor="middle">{node.label}</text>
            <text className="node-meta" x={node.x} y={node.y + 63} textAnchor="middle">{node.meta}</text>
          </g>
        )
      })}
      <g className="graph-legend" transform="translate(24 22)">
        <circle cx="4" cy="4" r="4" />
        <text x="16" y="8">PROPAGATION PATH / LIVE</text>
      </g>
    </svg>
  )
}

function WaterScene({ level, severity, confidence }: { level: number; severity: Severity; confidence: number }) {
  return (
    <div className="water-scene">
      <svg className="watershed-art" viewBox="0 0 720 700" role="img" aria-label="Animated river basin carrying a warning downstream">
        <defs>
          <linearGradient id="basinWater" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#b9ffe0" />
            <stop offset=".42" stopColor="#43daca" />
            <stop offset="1" stopColor="#2a7fbe" />
          </linearGradient>
          <linearGradient id="riverDepth" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#5eead4" stopOpacity=".9" />
            <stop offset="1" stopColor="#2f80b8" stopOpacity=".82" />
          </linearGradient>
          <radialGradient id="basinHalo">
            <stop offset="0" stopColor="#5eead4" stopOpacity=".22" />
            <stop offset="1" stopColor="#5eead4" stopOpacity="0" />
          </radialGradient>
          <filter id="waterGlow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="11" />
          </filter>
          <filter id="softShadow" x="-30%" y="-30%" width="160%" height="160%">
            <feDropShadow dx="0" dy="18" stdDeviation="17" floodColor="#001014" floodOpacity=".4" />
          </filter>
        </defs>

        <circle cx="360" cy="350" r="320" fill="url(#basinHalo)" />
        <g className="contour-lines">
          <path d="M36 312C88 211 138 91 272 62c148-32 199 86 323 101 67 8 102 45 100 102" />
          <path d="M19 363C94 274 123 138 271 100c133-35 207 72 327 92 67 11 83 64 78 118" />
          <path d="M35 427c70-67 93-211 238-267 125-48 216 48 329 69 63 12 91 66 74 132" />
          <path d="M73 489c68-76 107-219 229-267 118-46 206 30 300 58 48 14 83 57 77 111" />
          <path d="M126 544c59-80 106-194 204-241 112-54 184 8 265 47 41 20 62 65 48 110" />
          <path d="M184 594c58-84 103-171 183-209 91-43 146 5 200 49 32 25 44 65 25 104" />
        </g>

        <g className="basin-islands" filter="url(#softShadow)">
          <path d="M73 222c45-89 150-150 235-133 57 12 92 49 134 69-80 13-133 46-172 102-62 88-116 99-197 62-31-14-25-51 0-100Z" />
          <path d="M455 385c58-53 137-65 188-17 40 37 43 111 10 163-31 48-87 78-151 70-69-9-106-67-90-126 9-34 19-67 43-90Z" />
        </g>

        <path className="river-bank" d="M-8 61C90 82 88 169 186 190c99 22 173-29 225 33 47 56-30 113 15 160 50 54 145 8 195 61 44 48 25 133 103 178" />
        <path className="river-body" d="M-8 61C90 82 88 169 186 190c99 22 173-29 225 33 47 56-30 113 15 160 50 54 145 8 195 61 44 48 25 133 103 178" />
        <path className="river-shine" d="M-8 61C90 82 88 169 186 190c99 22 173-29 225 33 47 56-30 113 15 160 50 54 145 8 195 61 44 48 25 133 103 178" />
        <path className="flow-particles" d="M-8 61C90 82 88 169 186 190c99 22 173-29 225 33 47 56-30 113 15 160 50 54 145 8 195 61 44 48 25 133 103 178" />

        <g className="basin-city city-a" transform="translate(176 221)">
          <rect x="-30" y="-22" width="60" height="44" rx="8" />
          <path d="M-17 8V-3h10V8M1 8v-18h11V8M-20-12h39" />
          <circle cx="0" cy="0" r="39" />
          <circle cx="0" cy="0" r="52" />
        </g>
        <g className="basin-city city-b" transform="translate(420 378)">
          <rect x="-30" y="-22" width="60" height="44" rx="8" />
          <path d="M-17 8V-3h10V8M1 8v-18h11V8M-20-12h39" />
          <circle cx="0" cy="0" r="39" />
          <circle cx="0" cy="0" r="52" />
        </g>
        <g className="basin-city city-c critical" transform="translate(618 516)">
          <rect x="-31" y="-23" width="62" height="46" rx="8" />
          <path d="M0-13v26M-13 0h26" />
          <circle cx="0" cy="0" r="39" />
          <circle cx="0" cy="0" r="52" />
        </g>

        <g className="scene-label source-label" transform="translate(59 116)">
          <rect width="133" height="42" rx="7" />
          <circle cx="17" cy="21" r="4" />
          <text x="30" y="18">SOURCE SIGNAL</text>
          <text x="30" y="31">YAMUNA GAUGE</text>
        </g>
        <g className="scene-label impact-label" transform="translate(489 584)">
          <rect width="165" height="42" rx="7" />
          <circle cx="17" cy="21" r="4" />
          <text x="30" y="18">EARLIEST IMPACT</text>
          <text x="30" y="31">HOSPITAL · 38 MIN</text>
        </g>
      </svg>

      <div className="water-readout">
        <div className="level-vessel" aria-hidden="true">
          <span className="vessel-fill"><i /><i /></span>
          <b className="level-tick tick-a" />
          <b className="level-tick tick-b" />
          <b className="level-tick tick-c" />
        </div>
        <div className="readout-copy">
          <small>OBSERVED WATER LEVEL</small>
          <strong>{level.toFixed(2)}<sup>m</sup></strong>
          <span><StatusDot severity={severity} /> {severityLabel[severity]} · {confidence}% confidence</span>
        </div>
      </div>

      <span className="droplet droplet-a" />
      <span className="droplet droplet-b" />
      <span className="droplet droplet-c" />
    </div>
  )
}

function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [language, setLanguage] = useState<'EN' | 'HI'>('EN')
  const [step, setStep] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [selectedImpact, setSelectedImpact] = useState(impacts[0].id)
  const current = scenarioSteps[step]
  const selected = impacts.find((impact) => impact.id === selectedImpact) ?? impacts[0]

  useEffect(() => {
    document.documentElement.dataset.theme = theme
  }, [theme])

  useEffect(() => {
    if (!playing) return
    if (step >= scenarioSteps.length - 1) {
      setPlaying(false)
      return
    }
    const timer = window.setTimeout(() => setStep((value) => Math.min(value + 1, scenarioSteps.length - 1)), 1350)
    return () => window.clearTimeout(timer)
  }, [playing, step])

  const progress = useMemo(() => ((step + 1) / scenarioSteps.length) * 100, [step])

  const startReplay = () => {
    if (step === scenarioSteps.length - 1) setStep(0)
    setPlaying((value) => !value)
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to main content</a>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="Ripple home">
          <RippleMark />
          <span><strong>Ripple</strong><small>DEPENDENCY INTELLIGENCE</small></span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#console">Console</a>
          <a href="#trace">Trace</a>
          <a href="#advisory">Advisory</a>
          <a href="#system">System</a>
        </nav>
        <div className="header-actions">
          <button className="text-button" onClick={() => setLanguage(language === 'EN' ? 'HI' : 'EN')} aria-label="Change language">
            {language} <span>/ {language === 'EN' ? 'HI' : 'EN'}</span>
          </button>
          <button className="theme-button" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>
            <span className="theme-orbit" />
          </button>
          <a className="header-cta" href="#console">Open console <ArrowIcon /></a>
        </div>
      </header>

      <main id="main">
        <section className="hero" id="top">
          <div className="hero-grid-overlay" />
          <div className="hero-copy">
            <div className="eyebrow"><StatusDot severity="watch" /> YAMUNA REPLAY · SYSTEM ARMED</div>
            <h1>See the shortage<br /><em>before it arrives.</em></h1>
            <p className="hero-lede">Ripple turns a river warning into a traceable chain of downstream consequences—so hospitals, water teams, and public services get time to act.</p>
            <div className="hero-actions">
              <a className="primary-button" href="#console">Run the scenario <ArrowIcon /></a>
              <a className="secondary-button" href="#trace">Follow the signal <ArrowIcon down /></a>
            </div>
            <div className="hero-footnote"><span>DEMO DATA / JUL 2023 REPLAY</span><span>NOT AN OFFICIAL PUBLIC WARNING</span></div>
          </div>

          <div className="hero-visual">
            <WaterScene level={current.level} severity={current.severity} confidence={current.confidence} />
          </div>
          <div className="waterline-divider" aria-hidden="true">
            <svg viewBox="0 0 1600 90" preserveAspectRatio="none">
              <path className="wave-back" d="M0 49c158-42 262 26 415 5 169-23 246-65 421-32 171 32 261 63 414 28 145-34 231-27 350 6V90H0Z" />
              <path className="wave-front" d="M0 62c164-27 278 22 432-2 154-24 276-37 417-4 154 37 260 33 400 4 148-31 234-11 351 10v20H0Z" />
            </svg>
          </div>
        </section>

        <section className="signal-strip" aria-label="Current scenario statistics">
          <div><span>01</span><strong>206.12 m</strong><small>PEAK LEVEL / REPLAY</small></div>
          <div><span>02</span><strong>3 assets</strong><small>TREATMENT PLANTS WATCHED</small></div>
          <div><span>03</span><strong>38 min</strong><small>EARLIEST SERVICE IMPACT</small></div>
          <div><span>04</span><strong>4 hops</strong><small>FULL CAUSAL TRACE</small></div>
        </section>

        <section className="section-block console-section" id="console">
          <SectionHeading
            number="01"
            label="LIVE SCENARIO"
            title={<>One event. <em>Every consequence.</em></>}
            copy="Replay a historical river-level rise and watch Ripple calculate which connected services may be affected, when, and why."
          />

          <div className="command-frame">
            <div className="command-topbar">
              <div className="command-title"><StatusDot severity={current.severity} /><span>YAMUNA / DELHI</span><small>CONTROLLED REPLAY</small></div>
              <div className="command-clock"><span>OBSERVED</span><strong>{current.time}:00 IST</strong></div>
              <button className="replay-button" onClick={startReplay}>
                <PlayIcon pause={playing} /> {playing ? 'Pause replay' : step === scenarioSteps.length - 1 ? 'Restart replay' : 'Play replay'}
              </button>
            </div>
            <div className="replay-track">
              <div className="track-fill" style={{ width: `${progress}%` }} />
              {scenarioSteps.map((item, index) => (
                <button
                  key={item.time}
                  className={index === step ? 'active' : index < step ? 'past' : ''}
                  onClick={() => { setPlaying(false); setStep(index) }}
                  aria-label={`Jump to ${item.time}, ${item.event}`}
                >
                  <i /><span>{item.time}</span>
                </button>
              ))}
            </div>

            <div className="command-grid">
              <div className="graph-panel">
                <div className="panel-header"><span>DEPENDENCY SURFACE</span><small>GRAPH v0.3 / 08 NODES</small></div>
                <CascadeGraph activeNodes={current.activeNodes} selected={selectedImpact} onSelect={(id) => {
                  if (impacts.some((impact) => impact.id === id)) setSelectedImpact(id)
                }} />
                <div className="graph-caption"><span>Click a facility node to inspect its path</span><span>Source → Treatment → Zone → Service</span></div>
              </div>
              <aside className="event-panel">
                <div className="panel-header"><span>EVENT LOG</span><small>{step + 1} / {scenarioSteps.length}</small></div>
                <div className={`event-status ${current.severity}`}>
                  <StatusDot severity={current.severity} />
                  <span>{severityLabel[current.severity]}</span>
                  <b>{current.confidence}% confidence</b>
                </div>
                <p className="event-time">{current.elapsed} · {current.time} IST</p>
                <h3>{current.event}</h3>
                <p>{language === 'EN' ? current.detail : current.detailHi}</p>
                <Hydrograph step={step} />
                <div className="source-row"><span>SOURCE</span><b>CWC replay / declared demo input</b></div>
              </aside>
            </div>
          </div>
        </section>

        <section className="section-block trace-section" id="trace">
          <SectionHeading
            number="02"
            label="EXPLAINABILITY"
            title={<>Never just an alert.<br /><em>Always a reason.</em></>}
            copy="Every recommendation carries its evidence, dependency path, estimated arrival time, confidence, and a human-readable next action."
          />

          <div className="trace-layout">
            <div className="impact-list" role="list" aria-label="Predicted service impacts">
              {impacts.map((impact, index) => (
                <button key={impact.id} className={selectedImpact === impact.id ? 'selected' : ''} onClick={() => setSelectedImpact(impact.id)} role="listitem">
                  <span className="impact-index">0{index + 1}</span>
                  <span className="impact-copy"><small>{impact.type}</small><strong>{impact.name}</strong></span>
                  <span className="impact-eta"><small>ETA</small><b>{impact.eta}</b></span>
                  <StatusDot severity={impact.severity} />
                </button>
              ))}
            </div>
            <div className="explain-card">
              <div className="explain-head">
                <div><span className={`severity-pill ${selected.severity}`}>{severityLabel[selected.severity]}</span><small>WHY THIS ALERT?</small></div>
                <strong>{selected.confidence}<sup>%</sup></strong>
              </div>
              <h3>{selected.name}</h3>
              <p className="explain-summary">Potential supply interruption in <b>{selected.eta}</b>. This is an inferred operational impact, not a flood prediction for the facility itself.</p>
              <ol className="causal-path">
                {selected.path.map((node, index) => (
                  <li key={node}><span>{String(index + 1).padStart(2, '0')}</span><b>{node}</b>{index < selected.path.length - 1 && <i />}</li>
                ))}
              </ol>
              <div className="action-box"><small>RECOMMENDED ACTION</small><p>{language === 'EN' ? selected.action : selected.actionHi}</p></div>
              <div className="explain-meta"><span>MODEL <b>DETERMINISTIC v0.3</b></span><span>GRAPH <b>ASSUMPTION-LABELLED</b></span></div>
            </div>
          </div>
        </section>

        <section className="section-block advisory-section" id="advisory">
          <SectionHeading
            number="03"
            label="ACTION LAYER"
            title={<>Complex model in.<br /><em>Clear action out.</em></>}
            copy="Operators get the full trace. Facilities get only the verified facts and the next safe action—in English or Hindi."
          />

          <div className="advisory-stage">
            <div className="advisory-copy">
              <div className="micro-label">CONTROLLED COMMUNICATION</div>
              <h3>AI can simplify the language.<br />It cannot change the facts.</h3>
              <p>Risk, timing, confidence, and action codes come from Ripple’s deterministic cascade engine. Any generated translation is schema-checked before a human approves delivery.</p>
              <ul>
                <li><span>01</span> Deterministic impact calculation</li>
                <li><span>02</span> Bilingual template or Bedrock translation</li>
                <li><span>03</span> Schema validation + human approval</li>
              </ul>
            </div>
            <div className="phone-shell">
              <div className="phone-top"><span>RIPPLE ADVISORY</span><StatusDot severity="critical" /></div>
              <div className="phone-alert">
                <div className="phone-alert-head"><span>WATER SUPPLY</span><b>WARNING</b></div>
                <h4>{language === 'EN' ? 'Prepare for possible supply disruption' : 'Sambhavit water supply disruption ke liye taiyaar rahein'}</h4>
                <p>{language === 'EN'
                  ? 'North District Hospital may experience reduced municipal supply in approximately 38 minutes.'
                  : 'North District Hospital mein lagbhag 38 minute mein municipal supply kam ho sakti hai.'}</p>
                <div className="phone-metric"><span>EXPECTED IN</span><strong>00:38:00</strong></div>
                <div className="phone-action"><small>NEXT ACTION</small><p>{language === 'EN' ? selected.action : selected.actionHi}</p></div>
              </div>
              <div className="phone-footer"><span>DEMO ADVISORY · APPROVAL REQUIRED</span><button onClick={() => setLanguage(language === 'EN' ? 'HI' : 'EN')}>{language === 'EN' ? 'हिंदी में देखें' : 'View in English'}</button></div>
            </div>
            <div className="approval-stamp"><span>HUMAN</span><b>APPROVAL</b><small>REQUIRED</small></div>
          </div>
        </section>

        <section className="section-block system-section" id="system">
          <SectionHeading
            number="04"
            label="SYSTEM DESIGN"
            title={<>Small enough to demo.<br /><em>Built to expand.</em></>}
            copy="A focused event-driven architecture on AWS keeps the hackathon build credible, observable, and ready for additional cities and dependencies."
          />
          <div className="system-grid">
            {[
              ['01', 'Observe', 'S3 replay + EventBridge', 'Timestamped source events enter through one declared ingestion contract.'],
              ['02', 'Calculate', 'Lambda + DynamoDB', 'A deterministic graph traversal computes impact time, severity, confidence, and causal path.'],
              ['03', 'Explain', 'API Gateway + React', 'One response powers the operator trace, public advisory, timeline, and accessible list view.'],
              ['04', 'Communicate', 'Bedrock + SNS', 'Optional simplification and translation happen after facts are locked, then require approval.'],
            ].map(([number, title, tech, copy]) => (
              <article key={number}>
                <div className="system-card-top"><span>{number}</span><RippleMark /></div>
                <h3>{title}</h3><b>{tech}</b><p>{copy}</p>
              </article>
            ))}
          </div>
          <div className="principle-strip">
            <span>ONE OPERATING PRINCIPLE</span>
            <p>Hazard data becomes useful only when it reaches the person who can act—<em>with enough time and enough evidence.</em></p>
          </div>
        </section>

        <section className="closing-section">
          <div className="closing-rings"><i /><i /><i /><i /></div>
          <div className="eyebrow"><StatusDot severity="watch" /> BUILT FOR ENVIRONMENTAL HACKS</div>
          <h2>Make every warning<br /><em>travel further.</em></h2>
          <p>From river signal to service action. One traceable ripple at a time.</p>
          <a className="primary-button" href="#console">Replay the chain <ArrowIcon /></a>
        </section>
      </main>

      <footer>
        <div className="footer-brand"><RippleMark /><strong>Ripple</strong><span>DEPENDENCY-AWARE EARLY WARNING</span></div>
        <div><small>SCENARIO</small><span>Yamuna · July 2023 replay</span></div>
        <div><small>STATUS</small><span>Hackathon prototype · Assumption-labelled</span></div>
        <div className="footer-end"><span>© 2026 RIPPLE</span><a href="https://github.com/Raghav7-tech/Ripple" target="_blank" rel="noreferrer">GITHUB ↗</a></div>
      </footer>
    </div>
  )
}

export default App
