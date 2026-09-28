# Design System

Original identity. Nothing is derived from the reference site's visual design. Implemented in `packages/ui` (Tailwind CSS preset + shadcn/ui primitives on Radix, restyled).

## 1. Brand direction

Calm, clinical-precise, warm. Not the "red/white pathology lab" look. Deep teal conveys trust and medicine, coral is the action accent, and neutrals are slightly warm to avoid a sterile feel.

## 2. Tokens (CSS variables; light / dark)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--brand-600` | `#0F6E6A` | `#3FB8B0` | Primary actions, links |
| `--brand-700` | `#0B5552` | `#5FCFC7` | Hover / pressed |
| `--brand-50` | `#E8F5F4` | `#0E2A29` | Tinted surfaces |
| `--accent-500` | `#E8674A` | `#F08467` | Offers, badges, highlights (never for errors) |
| `--bg` | `#FBFAF8` | `#0F1413` | Page |
| `--surface` | `#FFFFFF` | `#161D1C` | Cards |
| `--text` | `#1B2524` | `#E6ECEB` | Body |
| `--text-muted` | `#5A6664` | `#9AA8A6` | Secondary (≥ 4.5:1 on bg) |
| `--border` | `#E2E6E4` | `#26302F` | Dividers |
| `--success` / `--warning` / `--danger` / `--info` | `#1E8A4C` / `#B7791F` / `#C0392B` / `#2563EB` | lighter equivalents | Status |
| **Result flags** | N: text · L/H: `--warning` + ↓/↑ glyph · Critical: `--danger` bold + "!" | | Never colour-only |

All text pairs are checked to WCAG AA (4.5:1 body, 3:1 large and UI). Dark mode applies to the console (`prefers-color-scheme` + toggle). The patient web ships light first, with dark as a P2 item.

## 3. Typography

- Latin: **Inter** (variable). Bangla: **Noto Sans Bengali** (Hind Siliguri as an alternative). Both are loaded as a single `font-family` stack so mixed-script text aligns. Bangla gets +2 % line-height.
- Scale (rem): 0.75 / 0.875 / 1 / 1.125 / 1.25 / 1.5 / 1.875 / 2.25 / 3. Body 1 rem (16 px) minimum on mobile.
- Numerals: `font-variant-numeric: tabular-nums` in tables, prices and results. An optional Bangla-digit display setting is available.

## 4. Spacing, radius, elevation

- 4 px base grid: 4, 8, 12, 16, 24, 32, 48, 64.
- Radius: `sm 6px` (inputs, badges), `md 10px` (buttons, cards), `lg 16px` (sheets, modals), `full` (chips).
- Elevation: 3 levels, soft and low-contrast. Dark mode uses a border instead of a shadow.

## 5. Breakpoints

`sm 640 · md 768 · lg 1024 · xl 1280 · 2xl 1536`. Patient web is designed at 360 px first. Console is designed at 1280 and must remain usable at 768 (tables become cards below `md`).

## 6. Components (`packages/ui`)

**Primitives:** Button (primary / secondary / ghost / danger; sm / md / lg; loading state), Input, Textarea, Select, Combobox, DatePicker (Bangla locale), PhoneInput (+880 fixed), MoneyInput, Checkbox, Radio, Switch, Modal, Drawer, Sheet (mobile), Dropdown, Tabs, Tooltip, Toast, Alert, Badge, Skeleton, Avatar.
**Composites:** Card, DataTable (TanStack Table + virtualisation, column filters, bulk select, CSV export), Pagination, SearchBox (with autocomplete groups), FileUploader (drag/drop, progress, type/size pre-check), EmptyState, ErrorState (with retry), StatusTimeline, StatCard, ConfirmDialog (types the entity name for destructive actions).
**Domain:** TestCard, PackageCard (included-tests count + "you save"), PriceTag (৳, strike-through MRP), ReportCard, BookingStepper, SlotPicker (grouped morning/afternoon, capacity hints), PatientPicker (+ inline "add family member"), AddressForm (BD hierarchy), ResultFlag, TrendChart (reference band shaded), BarcodeLabel, QRBadge.

Rule: a component is built once in `packages/ui`. Apps compose it and never fork it.

## 7. Patterns

- **Booking stepper** (mobile): sticky bottom summary bar (item count, total, CTA). Steps are collapsible, and completed steps show a one-line summary with "Change".
- **States:** every data view implements loading (skeleton matching the layout), empty (illustration + next action), error (message + retry + request_id for support) and success.
- **Forms:** React Hook Form + Zod schemas generated from OpenAPI where possible. Inline errors below fields, linked with `aria-describedby`. Server field errors map back onto fields.
- **Console:** left sidebar (collapsible, permission-filtered), top bar (branch switcher, global search, notifications), list → drawer detail/edit, bulk action bar.
- **Collector UI:** one assignment per screen, large touch targets (≥ 48 px), primary action pinned to the bottom, offline banner.

## 8. Accessibility checklist

Semantic landmarks · skip link · visible focus ring (`2px brand + 2px offset`) · all controls keyboard-operable (Radix) · labels for every input · error summaries announced (`role="alert"`) · touch targets ≥ 44 px · respects `prefers-reduced-motion` · charts have tabular alternatives · language attribute switches to `bn` for Bangla content.

## 9. Voice and copy

Plain, reassuring, precise. Bangla and English written natively, not machine-translated. Never alarming about results. Critical values are never shown to patients before verification, and patient-facing copy avoids diagnostic language ("outside the reference range" rather than "abnormal / disease").
