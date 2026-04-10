# AWAP-AI — UI/UX Build Prompt for Antigravity

## Mission

Build the most visually stunning, technically flawless, production-grade security operations dashboard ever created. This is not a generic admin panel. This is a **cyber warfare command center** — the UI should feel like something operators at a tier-1 red team firm would use and be proud of. Every pixel, every animation, every transition must be intentional, polished, and smooth.

> **Quality Bar:** If it doesn't look better than Vercel's dashboard, Linear's UI, and Datadog combined — keep going.

---

## Aesthetic Direction

**Theme:** Dark. Always dark. Deep space black (`#080B14`) base with layered depth using slightly lighter panels (`#0D1117`, `#111827`). No pure black. No flat backgrounds.

**Accent System:**
- Primary: Electric cyan `#00D4FF` — for active states, live indicators, and primary CTAs
- Danger: Neon red `#FF2D55` — CRITICAL severity, abort actions, destructive states
- Warning: Acid amber `#FFB800` — HIGH severity, caution states
- Success: Phosphor green `#00FF88` — confirmed findings, scan complete, low severity
- Muted: Steel blue-gray `#4A5568` — borders, disabled states, secondary text

**Typography:**
- Display / Headers: `JetBrains Mono` or `Space Mono` — monospaced feels native to security tooling, creates a hacker-terminal authenticity
- Body / UI: `IBM Plex Sans` — technical, clinical, readable at small sizes
- Data / Numbers: `Fira Code` — for CVSS scores, timestamps, CVE IDs, hex values
- All headings should feel architectural and precise. No rounded soft fonts anywhere.

**Visual Language:**
- Glassmorphism panels with `backdrop-filter: blur(12px)` and `border: 1px solid rgba(0, 212, 255, 0.08)`
- Subtle scan-line overlay texture across the entire background (CSS repeating gradient, 1px lines, 2% opacity) — like a high-end CRT monitor
- Grid mesh background (SVG pattern, very faint cyan lines) on dashboard hero area
- Corner bracket decorations `⌐ ¬` on cards and panels — geometric, tactical
- Thin cyan horizontal rule separators that pulse once on load
- Numbers and stats should feel "counting up" — always animate from 0 on page load

---

## Animation Requirements

Every animation must be **smooth, purposeful, and performant** (60fps, GPU-accelerated). Use `transform` and `opacity` only — never animate `width`, `height`, or `top/left`.

### Page Load Sequence
1. Background grid fades in (0–200ms)
2. Sidebar slides in from left with staggered nav items (200–600ms, 60ms delay each)
3. Header bar drops down (300ms ease-out)
4. Dashboard cards reveal with staggered fade-up (400–900ms, 80ms delay each)
5. Stats count up from 0 to actual values (800ms ease-out, `requestAnimationFrame`)
6. Live feed starts populating with a typewriter/append effect

### Micro-interactions
- **Hover on cards:** `transform: translateY(-2px)` + box-shadow brightens (150ms ease)
- **Hover on nav items:** cyan left-border slides in from bottom (200ms), background tint appears
- **Button press:** `transform: scale(0.97)` (80ms) snap-back (120ms) — feels tactile
- **Severity badges:** pulse animation on CRITICAL (2s infinite glow pulse)
- **Toggle switches:** smooth slide with color transition (200ms cubic-bezier)
- **Modals:** backdrop blur fades in (200ms), panel scales from `0.95` to `1.0` + fade (250ms)
- **Tooltips:** appear with `translateY(4px) → 0` + fade (150ms)
- **Dropdown menus:** height-animate open with staggered item fade-in (30ms per item)

### Data & Live Elements
- **Progress bars:** animated fill with shimmer sweep on completion
- **Live request feed:** new rows slide in from top, pushing existing rows down — smooth, not jumpy. Max 50 rows, old ones fade out from bottom
- **Attack graph nodes:** spring-physics layout (use `d3-force`). New nodes appear with scale-in (300ms spring). Edges draw themselves (SVG `stroke-dashoffset` animation)
- **Charts:** all Recharts data animates in on mount (`isAnimationActive={true}`, 1200ms)
- **Scan phase indicator:** active phase pulses, completed phases check with a draw animation
- **WebSocket data:** arriving findings slide in from the right into the findings stream
- **CVSS score ring:** SVG circle that draws itself in (1s ease-out) with the number counting up inside
- **Scanning status dot:** triple-ring sonar pulse when a scan is active

### Page Transitions
- Route changes: current page fades out (150ms), new page fades + slides up (250ms)
- Use `Framer Motion` `AnimatePresence` for all route transitions

---

## Screen-by-Screen UI Specification

---

### Screen 1: Main Dashboard

**Layout:** Full-width dark canvas. Fixed sidebar (240px). Top header bar (56px). Content area fills remaining space.

**Header Bar:**
- Left: AWAP-AI logo (geometric hexagon icon + wordmark in Space Mono, cyan)
- Center: Global search bar (`⌘K` shortcut) — dark input, cyan focus ring, search icon left-aligned, keyboard shortcut hint right-aligned
- Right: Active scan count pill (cyan, pulsing dot), notification bell (with red dot badge), user avatar with dropdown

**Sidebar:**
- Dark panel `#0D1117` with 1px right border (cyan, 6% opacity)
- Logo section at top
- Nav sections: WORKSPACE (Targets, Active Scans), INTELLIGENCE (Findings, Analytics), OUTPUT (Reports), PLATFORM (Settings, Team)
- Active item: filled cyan left border + cyan text + very subtle cyan background tint
- Hover: same but lighter
- Bottom: platform version, docs link, keyboard shortcuts link

**Hero Stats Row (4 cards):**
- Active Scans | Critical Findings | Endpoints Discovered | Scan Velocity (req/s)
- Each card: glassmorphism panel, large monospaced number (counts up on load), small label, tiny sparkline chart in corner, colored accent based on metric type
- CRITICAL count card uses red accent and pulses if value > 0

**Live Feed (center, 60% width):**
- Title: "LIVE ACTIVITY FEED" in small caps, cyan, with live indicator dot
- Scrolling list of events: recon hits, crawled endpoints, confirmed findings — each with timestamp, type badge, and message
- Color-coded left border by event type (cyan=recon, amber=crawl, red=finding, green=complete)
- Auto-scrolls to bottom, user can pause by hovering

**Recent Findings Table (right panel, 40% width):**
- "RECENT FINDINGS" header with count badge
- Table: severity badge, vulnerability class, target, timestamp
- Severity badges are colored pills: CRITICAL (red+glow), HIGH (amber), MEDIUM (yellow), LOW (blue), INFO (gray)
- Row hover: subtle background highlight, cursor pointer
- Click opens Finding Detail as a side sheet (slides in from right)

---

### Screen 2: Target Management

**Layout:** Full content area. Header with "TARGETS" title + "Add Target" button (primary cyan).

**Target Grid (cards, 3-column):**
- Each card: domain name (large, monospaced), status badge (ACTIVE/SCANNING/COMPLETE/PAUSED), last scan timestamp, finding severity breakdown (mini horizontal bar: red/amber/yellow/blue proportional), quick action buttons (Scan, View, Pause, Delete)
- Status badge for SCANNING has a rotating radar animation
- Card border glows subtly cyan when a scan is actively running on that target

**Add Target Wizard (full-screen modal overlay):**
- 4-step wizard with progress indicator at top (steps connected by animated line)
- Step 1: URL input with live URL validation (green checkmark animates in when valid)
- Step 2: Scope file upload (drag-and-drop zone with dashed cyan border, upload icon, accepts .txt/.json) + manual scope rules editor
- Step 3: Scan profile selector (6 profile cards: Quick/Standard/Full/API/Stealth/Auth — each with icon, description, rate/depth info. Selected state: cyan border + checkmark)
- Step 4: Authorization confirmation — red warning box, checkbox "I confirm I have explicit written authorization to test this target", text input for authorization reference, submit button stays disabled until checked
- Each step transition: slide left/right with fade

---

### Screen 3: Live Scan Monitor

**Layout:** Immersive full-canvas layout. This screen should feel like a mission control center.

**Top Bar:**
- Target name + scan ID + started timestamp
- Scan phase stepper (8 phases): each phase is a node connected by a line. Completed = filled green circle + checkmark. Active = cyan circle with rotating ring. Pending = gray circle. Connecting lines fill cyan as phases complete.
- Overall progress bar (full width, animated fill, shimmer effect)
- Right: Abort button (red), Pause button (amber), Adjust Rate slider

**4-Quadrant Layout:**

**Top-Left — Live Request Stream:**
- Dark terminal-style panel with monospace font
- New requests appear at top, scroll down
- Format: `[timestamp] METHOD /path/endpoint — STATUS — Xms`
- Color by status: 200 (green), 3xx (blue), 4xx (amber), 5xx (red), timeout (gray)
- Scan rate indicator: "847 req/min" counter updates live

**Top-Right — Attack Graph:**
- Cytoscape.js / D3-force graph
- Nodes: domains (hexagon), endpoints (circle), confirmed vulnerabilities (diamond, glowing red/amber)
- Edges: crawl paths (thin gray), exploitation relationships (red dashed)
- New nodes spring into place with physics animation
- Click a vulnerability node: side panel appears with finding summary
- Zoom/pan enabled. "Reset View" button in corner.

**Bottom-Left — Live Findings Stream:**
- Each finding slides in from right as it's confirmed
- Card: severity badge (glowing), vuln class, endpoint, payload snippet
- CRITICAL findings trigger a full-width flash effect (brief red border pulse on the whole panel)
- Stacks up, scrollable

**Bottom-Right — Resource Meters:**
- CPU usage: animated arc gauge
- Memory: horizontal bar with fill animation
- Active connections: live number counter
- Request rate: real-time line sparkline (last 60 seconds)
- OOB callbacks received: counter with green flash on increment

---

### Screen 4: Vulnerability Finding Detail

**Layout:** Opens as a full-page route OR a right-side drawer (820px wide). Both versions must be implemented.

**Header:**
- Vulnerability name (large, monospaced)
- Severity badge (oversized, glowing) + CVSS score (large number, color-coded) + CVSS vector string (small, monospace)
- CWE ID + OWASP category chips
- Timestamp + scan ID + status dropdown (Confirmed / False Positive / Accepted Risk)

**CVSS Score Visualization:**
- SVG circular gauge that draws itself in on load
- Score number counts up
- Color transitions from green → yellow → amber → red based on score

**Evidence Panel (tabbed):**
- Tab 1 "HTTP Request": Raw request with full syntax highlighting (method in cyan, headers in amber, body in white). Copy button. "Send to Burp" button.
- Tab 2 "HTTP Response": Status line highlighted, response headers, body with payload reflection highlighted in red
- Tab 3 "Screenshot": Full-page screenshot in lightbox with zoom
- Payload is shown in a highlighted code block with the injection point marked

**PoC Section:**
- Tabbed: curl | Python | Burp XML
- Syntax highlighted code blocks
- Copy button on each (shows "Copied!" with checkmark for 2s)

**Remediation Panel:**
- Expandable section with OWASP link
- Code fix example in syntax-highlighted block (auto-detects language from target stack)

**Actions Bar (sticky bottom):**
- Mark Verified | Mark False Positive | Assign To | Export Finding | Previous Finding ← → Next Finding

---

### Screen 5: Security Analytics

**Layout:** Dashboard-style analytics page. Dense information, beautiful data viz.

**Filters Row:**
- Date range picker, target selector (multi), severity filter (chip toggles), vuln class filter

**Row 1 — Overview KPIs (5 cards):**
Total Findings | Critical+High | False Positive Rate | Avg CVSS Score | Remediation Rate

**Row 2 — Main Charts (2-column):**
- Left: Findings Over Time (area chart, stacked by severity, animated, gradient fill)
- Right: Vulnerability Class Distribution (animated donut chart, hover shows count + % + CVSS avg)

**Row 3 — Heatmaps & Tables:**
- Left: Attack Surface Treemap (D3 treemap, endpoint groups sized by finding count, color by max severity)
- Right: Top Vulnerable Endpoints table (endpoint URL, finding count, max severity, last seen — sortable)

**Row 4 — Performance:**
- Scan velocity over time (line chart)
- Payload success rate by vuln class (horizontal bar chart)
- False positive rate trend (line chart)

All charts: dark background, thin grid lines (3% opacity), smooth animations on load and filter change, custom tooltips (glassmorphism style).

---

### Screen 6: Report Builder

**Layout:** Split-pane. Left 40% = configuration. Right 60% = live preview.

**Left Panel:**
- Template selector: 6 large cards with icons (Executive / Technical / Developer / Compliance / Differential / Bug Bounty). Selected state glows cyan.
- Findings selector: searchable multi-select list. Each finding shows severity badge + name. "Select All / None" controls. Drag to reorder.
- Customization section: company name text input, logo upload, report header/footer text, CVSS score override toggles
- Export buttons row: PDF | DOCX | JSON | Markdown | CSV — each as a distinct styled button with format icon

**Right Panel (Live Preview):**
- Rendered report preview in a contained scroll area (white background inside dark chrome — intentional contrast)
- Updates live as user changes config
- Smooth re-render transitions (fade in/out)
- Zoom controls for preview

---

## Component Library Standards

Build a reusable component library before building screens. Every component must be pixel-perfect.

### Required Components:
- `<SeverityBadge severity="CRITICAL|HIGH|MEDIUM|LOW|INFO" />` — with glow variants
- `<CvssGauge score={9.8} animated />` — SVG ring gauge
- `<StatCard label="" value={} trend={} sparkline={[]} />` — animated on mount
- `<LiveFeed items={[]} />` — auto-scrolling with slide-in animations
- `<CodeBlock language="" copyable />` — syntax highlighted, dark
- `<ScanPhaseIndicator phases={[]} currentPhase={} />` — animated stepper
- `<AttackGraph findings={[]} endpoints={[]} />` — D3 force graph
- `<GlassPanel>` — wrapper with glassmorphism style
- `<StatusDot status="scanning|complete|paused|error" />` — with animations
- `<AnimatedNumber value={} duration={800} />` — count-up on mount
- `<TacticalCard>` — corner bracket decoration + hover lift
- `<SonarPulse active={bool} />` — triple ring radar animation

---

## Animation Library Stack

```
Framer Motion       — page transitions, layout animations, AnimatePresence
GSAP (optional)     — complex timeline sequences (page load orchestration)
Recharts            — all charts (isAnimationActive + custom easing)
D3-force            — attack graph physics
CSS animations      — micro-interactions, pulses, shimmer (prefer CSS for performance)
```

All animations must respect `prefers-reduced-motion`. When reduced motion is preferred, eliminate all motion except critical state changes (no layout shifts, no count-ups, no transitions).

---

## WebSocket Integration

Connect to `ws://localhost:8000/ws/scan/{scan_id}` for live data.

Event types to handle:
```json
{ "type": "request_sent", "data": { "method", "url", "status", "duration_ms" } }
{ "type": "finding_confirmed", "data": { ...finding_schema } }
{ "type": "phase_change", "data": { "phase", "progress_pct" } }
{ "type": "scan_complete", "data": { "summary" } }
{ "type": "recon_hit", "data": { "type", "value" } }
```

The UI must handle connection drops gracefully (auto-reconnect with exponential backoff, show reconnecting state in header).

---

## Performance Requirements

- **First Contentful Paint:** < 1.2s
- **Time to Interactive:** < 2.5s
- **Animation frame rate:** 60fps — profile and fix any janky animations
- **Bundle size:** Code-split by route. No route chunk > 200KB gzipped.
- **Large data tables:** Virtualize with `react-virtual` or `@tanstack/virtual` — never render > 50 DOM rows
- **Chart data:** Downsample to max 500 points before rendering. Recharts struggles beyond this.
- **WebSocket messages:** Debounce UI updates at 100ms — don't re-render on every single message

---

## State Management

Use **Zustand** for global state. Structure:

```typescript
// stores/scanStore.ts
interface ScanStore {
  activeScan: Scan | null
  phase: ScanPhase
  findings: Finding[]
  requests: RequestLog[]
  metrics: ScanMetrics
  actions: { startScan, pauseScan, abortScan, addFinding, addRequest }
}

// stores/uiStore.ts
interface UIStore {
  selectedFinding: Finding | null
  sideDrawerOpen: boolean
  theme: 'dark'  // always dark
  actions: { openFinding, closeFinding, toggleDrawer }
}
```

Use **React Query** for all API calls (targets, findings, reports). Cache aggressively. Optimistic updates on status changes.

---

## API Integration

Base URL: `http://localhost:8000/api/v1`

Key endpoints to wire up:

```
GET    /targets                    → Target list
POST   /targets                    → Create target
GET    /targets/{id}/scans         → Scan history
POST   /scans                      → Start scan
GET    /scans/{id}                 → Scan detail + status
PATCH  /scans/{id}                 → Pause/resume/abort
GET    /scans/{id}/findings        → Findings list (paginated)
GET    /findings/{id}              → Finding detail
PATCH  /findings/{id}              → Update status/assignment
GET    /reports/templates          → Report templates
POST   /reports/generate           → Generate report
GET    /analytics/summary          → Dashboard KPIs
GET    /analytics/trends           → Chart data
```

All API calls must have:
- Loading skeleton states (not spinners — skeleton screens)
- Error states with retry button
- Empty states with descriptive message + action button

---

## Skeleton Loading States

Every data-dependent UI region needs a skeleton loader. Skeletons must:
- Match the exact shape/size of the content they replace
- Animate with a shimmer sweep (left-to-right gradient animation)
- Use `#1A2035` base with `#252D45` shimmer highlight
- Disappear with a fade-out (not a pop)

---

## Empty States

Design empty states that are beautiful and instructive, not just "No data found":

- **No targets yet:** Animated hexagon icon + "Add your first target to begin scanning" + "Add Target" button
- **No findings:** Green shield icon + "No vulnerabilities confirmed yet" (appears mid-scan) or "Clean scan — no vulnerabilities found" (after complete)
- **No scans:** Terminal-style animation suggesting typing a command + prompt to start first scan
- **No reports:** Document icon with subtle animation + prompt to generate first report

---

## Accessibility

- All interactive elements keyboard-navigable
- Focus rings: `outline: 2px solid #00D4FF` (not the browser default)
- ARIA labels on all icon buttons
- Screen reader announcements for live feed updates (`aria-live="polite"`)
- Color is never the only indicator of state (always pair color with icon or text)
- Contrast ratios: minimum 4.5:1 for body text, 3:1 for large text

---

## QA & Verification Checklist

> **CRITICAL INSTRUCTION:** After building each component and screen, you MUST self-verify the following before moving on. Do not proceed if any item fails.

### For every component:
- [ ] Renders correctly at 1280px, 1440px, 1920px viewport widths
- [ ] All props are typed with TypeScript interfaces (no `any`)
- [ ] Loading state implemented and tested
- [ ] Error state implemented and tested
- [ ] Empty state implemented and tested
- [ ] All animations run at 60fps (no layout thrash)
- [ ] Hover, focus, and active states all styled
- [ ] Keyboard navigation works
- [ ] No console errors or warnings

### For every API integration:
- [ ] Loading skeleton shows while fetching
- [ ] Error boundary catches and displays error gracefully
- [ ] Data validates against expected TypeScript type
- [ ] Retry logic works on failure
- [ ] Optimistic update reverts correctly on failure

### For every animation:
- [ ] Uses only `transform` and `opacity` (no `width/height/top/left`)
- [ ] Has `will-change: transform` where appropriate
- [ ] Respects `prefers-reduced-motion`
- [ ] Does not block interactivity (no `pointer-events: none` during transitions)
- [ ] Feels smooth — not bouncy, not slow, not instant

### For the full application:
- [ ] All 6 screens implemented and fully functional
- [ ] All WebSocket events handled and reflected in UI
- [ ] Navigation between all screens works
- [ ] No broken links, dead buttons, or unimplemented features
- [ ] Report export triggers file download (mock if backend not ready)
- [ ] Scan start → live monitor → findings → report full flow works end-to-end
- [ ] Dark theme consistent across every screen (no white flash, no light-mode leakage)
- [ ] All fonts load correctly (add Google Fonts / Bunny Fonts import)
- [ ] All icons consistent (use Lucide React throughout — no mixing icon sets)

---

## Final Standard

This UI must look and feel like it was built by a senior design engineer at a world-class security company. Every interaction should feel **inevitable** — like there was no other way it could have been designed.

If you are unsure whether something looks good enough: make it better. Push every detail. The bar is: a screenshot of this UI should be impressive enough to post on Dribbble or be featured on Mobbin.

**Build it once. Build it right. Make it unforgettable.**
