# UI Blueprint & Component Mapping: CyberShorts AI Web Management Console

## 1. Preserved DOM IDs & Existing Handlers
The following existing DOM elements and JavaScript triggers MUST be 100% preserved so existing functionality and tests continue working seamlessly:
- `#btn-run` -> `triggerRun()` -> Calls `POST /api/run-now`
- `#btn-scrape` -> `triggerScrape()` -> Calls `POST /api/scrape-now`
- `#terminal-logs` -> Terminal container displaying live logs
- Table headers & data columns: ID, Date, Headline/Title, Status, Cloud Storage, YouTube Short, Instagram, Facebook Reel

## 2. New Management Capabilities & Elements to Introduce
- **Prompt Creator Studio (`#prompt-form`, `#input-prompt`, `#select-category`, `#btn-create-prompt`)**:
  - Live on-demand video creation directly from the web interface.
  - Category selector: Frontier AI (`ai`), Offensive Cybersecurity (`cyber`), General Tech.
  - Interactive submission with tactile state transitions and inline progress notifications.
- **Publishing State Management Pill (`#btn-toggle-pause`, `#pill-publishing-status`, `#text-publishing-status`)**:
  - Live toggle between `🟢 ACTIVE (Auto-Publishing)` and `⏸️ PAUSED (Holding in Storage)`.
- **Dual-Timezone Live Telemetry Strip (`#card-utc-timer`, `#card-ist-timer`, `#card-daily-balance`)**:
  - Dynamic ticking countdowns to next YouTube drop (UTC) and Instagram/FB drop (IST).
  - Real-time UTC and IST clock synchronization.
  - Daily balance indicator: 1 Frontier AI + 1 Offensive Cybersecurity (`completed_today/MAX_VIDEOS_PER_DAY`).
- **Interactive Video Player Modal (`#modal-video-preview`, `#video-player-frame`, `#btn-close-modal`)**:
  - Plays generated 9:16 vertical video directly inside browser via `/api/video/{job_id}/stream`.
  - Accessible focus trapping, `Escape` key dismissal, backdrop click dismissal, and `overscroll-behavior: contain`.
  - Details panel showing Hook, Script, Duration, Voice Persona, and quick copy buttons.
- **System Settings Drawer / Modal (`#modal-settings`, `#btn-open-settings`)**:
  - Quick inspection of active timings, keys, voice rotation, and topics.
- **Enhanced Log Telemetry (`#log-filter-all`, `#log-filter-error`, `#log-filter-info`, `#btn-copy-logs`, `#btn-clear-terminal`)**:
  - Real-time log stream filtering and copy action.

## 3. Design Token Architecture & CSS Architecture
- **Tokens (`css/tokens.css` or embedded token block)**:
  - Font Sans: `system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
  - Font Mono: `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace`
  - Concentric Radius Law: $R_{\text{outer}} = R_{\text{inner}} + \text{padding} + \text{border}$
  - Colors: Cyberpunk Dark Palette (`#050811` base, `rgba(16, 26, 46, 0.85)` elevated, `rgba(12, 20, 36, 0.70)` cards, `#00e5ff` cyan, `#10b981` green, `#f59e0b` yellow, `#f87171` red, `#e879f9` purple)
  - Tabular numbers on all counters, clocks, IDs, and timestamps (`font-variant-numeric: tabular-nums`).
- **Motion (`css/motion.css`)**:
  - Micro-interactions 150ms–250ms with `:active` `scale(0.96)`.
  - Full `@media (prefers-reduced-motion: reduce)` support.
- **Accessibility (WCAG 2.2)**:
  - Text contrast $\ge 4.5:1$ against backgrounds.
  - Explicit `aria-label` on all icon controls.
  - Form validation messages adjacent to inputs, never blocking paste.

