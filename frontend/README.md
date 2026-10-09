# Ripple frontend

The frontend is an interactive prototype of Ripple's operator console and public advisory experience. It is built with React, TypeScript, Vite, custom SVG data visuals, and handcrafted CSS—no map tile service or UI component library is required.

## What works

- Five-step controlled replay of the Yamuna demonstration scenario
- Animated river-basin visual and live water-level readout
- Dependency graph connecting gauge, treatment plants, supply zones, and critical services
- Selectable facility impacts with causal path, ETA, confidence, and recommended action
- English/Hindi copy switching
- Dark/light themes
- Responsive desktop and mobile layouts
- Keyboard-accessible interactive controls and reduced-motion handling

The UI uses local demonstration data from `src/data/scenario.ts`. It does not call a backend yet and is not an official warning system.

## Local development

```bash
pnpm install
pnpm dev
```

## Production validation

```bash
pnpm typecheck
pnpm build
pnpm preview
```

## Source map

```text
frontend/
├── src/
│   ├── data/scenario.ts   Replay and impact demonstration data
│   ├── App.tsx            Experience, interactions, and SVG visualisations
│   ├── main.tsx           React entry point
│   └── styles.css         Design system, animation, and responsive layouts
├── index.html
├── package.json
└── vite.config.ts
```

## Next integration seam

Replace the local scenario arrays with a typed API client matching `../docs/API_CONTRACT.md`. Keep the current presentation contract stable: observed event, graph version, impact path, ETA, severity, confidence, source, and action code must arrive as deterministic fields from the backend.
