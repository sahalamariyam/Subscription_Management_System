---
name: Kinetic Ledger
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#464555'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#777587'
  outline-variant: '#c7c4d8'
  surface-tint: '#4d44e3'
  primary: '#3525cd'
  on-primary: '#ffffff'
  primary-container: '#4f46e5'
  on-primary-container: '#dad7ff'
  inverse-primary: '#c3c0ff'
  secondary: '#00687a'
  on-secondary: '#ffffff'
  secondary-container: '#57dffe'
  on-secondary-container: '#006172'
  tertiary: '#005338'
  on-tertiary: '#ffffff'
  tertiary-container: '#006e4b'
  on-tertiary-container: '#67f4b7'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e2dfff'
  primary-fixed-dim: '#c3c0ff'
  on-primary-fixed: '#0f0069'
  on-primary-fixed-variant: '#3323cc'
  secondary-fixed: '#acedff'
  secondary-fixed-dim: '#4cd7f6'
  on-secondary-fixed: '#001f26'
  on-secondary-fixed-variant: '#004e5c'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.025em
  display-lg-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: '600'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.025em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.035em
  numeric-metric:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  numeric-table:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

The design system establishes a high-density, authoritative visual language tailored for modern enterprise financial operations, recurring billing orchestration, and subscription lifecycle management. The brand identity balances institutional rigor with contemporary SaaS agility: clean, mathematically disciplined, and luminous. 

Targeted at CFOs, revenue operations leaders, and billing administrators, the UI evokes clarity, operational precision, and absolute system reliability under heavy data loads. 

The aesthetic is **Corporate / Modern** underpinned by functional minimalism:
- Razor-sharp structural grid rhythm with pure white cards hovering on cool slate canvas tones.
- High-contrast visual cues with an electric primary indigo signature, augmented by cyan accents for technical telemetry.
- Strict data clarity: zero decorative ornament, intentional reliance on tabular alignment, and semantic color discipline for risk, liquidity, and churn monitoring.

## Colors

The palette uses a deliberate hierarchy prioritizing immediate legibility, high contrast ratios (minimum 4.5:1 for body copy and 3:1 for interactive bounds), and unambiguous status signaling.

### Functional Roles & Tone Distribution

- **Primary Brand (`#4F46E5` / Indigo 600)**: Anchors primary execution triggers, high-priority interactive states, and active navigation nodes. Hover states transition down to `#4338CA` (Indigo 700), while subtle focus rings utilize `#EEF2FF` (Indigo 50) and `#C7D2FE` (Indigo 200).
- **Secondary Telemetry (`#06B6D4` / Cyan 500)**: Serves as an analytical accent for real-time telemetry, automated schedules, cohort projections, and API integration states.
- **Semantic Signaling**:
  - **Success / Expansion (`#10B981` / Emerald 500)**: Upgrades, paid invoices, healthy retention, ARR gains.
  - **Warning / Pending (`#F59E0B` / Amber 500)**: Approaching renewals, retrying payments, grace periods.
  - **Critical / Churn (`#F43F5E` / Rose 500)**: Failed transactions, immediate cancellations, chargebacks.
- **Surfaces & Neutral Structural Planes**:
  - Canvas Root: `#F8FAFC` (Slate 50) provides a soft, low-glare backdrop.
  - Surface Raised: `#FFFFFF` (Pure White) defines interactive cards, modals, and data tables.
  - Subtle Dividing Rule: `#E2E8F0` (Slate 200) standard border color across all containers.
  - Text Dominance: `#0F172A` (Slate 900) for primary headers, data values, and titles; `#64748B` (Slate 500) for metadata, labels, and secondary context.

## Typography

The typographical engine leverages **Inter** across all display, narrative, and tabular roles, unlocking maximum clarity across high-density financial layouts.

### Implementation Directives

- **Numeric Figures**: All ledger outputs, currency quantities, MRR indicators, and timestamp figures must enforce tabular lining features via OpenType configuration (`font-feature-settings: "tnum" 1, "cv05" 1`). This prevents vertical column drift across dynamic grids.
- **Hierarchy Separation**: Headlines from `headline-sm` upward employ slightly tightened tracking (`letter-spacing`) to balance weight in data dashboards. 
- **Labels & Micro-data**: `label-sm` applies uppercase transformations with deliberate tracking (`0.035em`) to clearly designate schema attributes, data statuses, and form anchors without visual noise.

## Layout & Spacing

The layout model is governed by a strict mathematical 4px spatial baseline. Elements align to increments of 4px (`space-xs: 4px`, `space-sm: 8px`, `space-md: 16px`, `space-lg: 24px`, `space-xl: 32px`).

### Grid Orchestration
- **Desktop (>= 1280px)**: 12-column fluid grid, 24px (`1.5rem`) gutters, 32px (`2rem`) outer canvas margins, max-width bound at 1600px for ultra-wide dashboards.
- **Tablet (768px - 1279px)**: 8-column layout, 20px gutters, 24px margins. Operational navigation collapses into an anchored persistent rail or standard drawer.
- **Mobile (< 768px)**: 4-column layout, 16px (`1rem`) gutters, 16px (`1rem`) margins. Multi-column financial metrics transform into vertical key-value lists or scrollable horizontally snap-aligned metric ribbons.

### Density Strategy
Financial workspaces require controlled visual density. Table cell padding strictly adheres to `8px 16px` for dense states and `12px 16px` for standard states. Component gaps prioritize relational proximity: inputs and their associated labels maintain a rigid 6px gap, grouping related fields within 16px containers.

## Elevation & Depth

Visual hierarchy uses a refined hybrid approach: **subtle boundary delineation combined with ambient low-opacity shadows**. Rather than heavy drop shadows, the system relies on boundary lines matched with soft atmospheric diffusion to maintain an architectural, technical plane.

### Elevation Hierarchy

- **Level 0 (Flat Canvas)**: `#F8FAFC` base plane. No shadow, no outline. Houses structural backdrops and empty grid areas.
- **Level 1 (Card & Module Resting)**: `#FFFFFF` surface accompanied by a crisp 1px solid border in `#E2E8F0` and an ambient micro-shadow: `0 1px 3px 0 rgba(15, 23, 42, 0.05), 0 1px 2px -1px rgba(15, 23, 42, 0.05)`.
- **Level 2 (Hover & Active Surfaces)**: Elevated cards, active table rows, and interactive pricing tiers transition into: `0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.05)`, maintaining border `#CBD5E1`.
- **Level 3 (Flyouts & Dropdowns)**: Action menus, date pickers, filter drawers, and tooltips utilize: `0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.04)` over a 1px border `#E2E8F0`.
- **Level 4 (Modals & Overlays)**: Subscription upgrade wizards, cancellation confirmations, and refund dialogues: `0 20px 25px -5px rgba(15, 23, 42, 0.1), 0 8px 10px -6px rgba(15, 23, 42, 0.05)` coupled with a modal backdrop wash of `#0F172A` at 40% opacity (`rgba(15, 23, 42, 0.40)`).

## Shapes

The design system follows a **Soft** curvature standard (`roundedness: 1` -> 0.25rem / 4px base radius). This controlled geometry aligns with enterprise data density, maintaining clean vertical and horizontal lines across large-scale data tables and complex financial dashboards.

### Radius Assignments
- **Micro Radius (4px / 0.25rem)**: Base inputs, buttons, checkboxes, tooltips, inline code blocks, and table row selection indicators.
- **Mid Radius (8px / 0.5rem - `rounded-lg`)**: Content cards, financial summary tiles, dropdown menus, flyouts, and metric blocks.
- **Macro Radius (12px / 0.75rem - `rounded-xl`)**: Top-level modals, multi-step subscription flows, and global layout containers.
- **Pill Exception (9999px)**: Specifically reserved for status badges, subscription tier tags, and monetary counter chips to distinguish metadata from interactive square-corner controls.

## Components

### Buttons
- **Primary**: Solid `#4F46E5` background, `#FFFFFF` text, 4px border radius. Hover: `#4338CA`. Active: `#3730A3`. Focus-visible: 2px offset with 2px ring in `#6366F1`. Padding: 8px 16px for medium; 6px 12px for compact table actions.
- **Secondary**: `#FFFFFF` background, 1px solid `#E2E8F0`, `#0F172A` text. Hover: `#F8FAFC` background with border `#CBD5E1`.
- **Destructive**: Solid `#F43F5E` background, `#FFFFFF` text. Used exclusively for immediate cancellation or subscription termination.

### Status Badges (Pills)
Engineered for real-time lifecycle tracking using 9999px pill radii, 2px 8px padding, `label-sm` typography, and matching border tints:
- **Active / Paid**: `#ECFDF5` background, `#059669` text, 1px solid `#A7F3D0`.
- **Trialing / In Review**: `#ECFEFF` background, `#0891B2` text, 1px solid `#A5F3FC`.
- **Past Due / Retrying**: `#FFFBEB` background, `#D97706` text, 1px solid `#FDE68A`.
- **Canceled / Failed**: `#FFF1F2` background, `#E11D48` text, 1px solid `#FECDD3`.

### Input Fields & Selectors
- Standard height: 36px (compact) and 40px (default).
- Surface: `#FFFFFF` fill, 1px solid `#CBD5E1`, 4px radius, text in `#0F172A`, placeholder in `#94A3B8`.
- Focus State: Border transitions to `#4F46E5` with an immediate outer glow of `0 0 0 3px rgba(79, 70, 229, 0.15)`.

### Cards & Financial Modules
- Root background `#FFFFFF`, 1px solid `#E2E8F0`, 8px radius, Level 1 elevation.
- Structure: Header section carries metric titles (`label-md` in `#64748B`) followed by prominent value indicators (`numeric-metric` in `#0F172A`) paired with inline delta badges (e.g., `+12.4% ARR`).

### Data Tables (Subscription & Ledger Engine)
- Header row: `#F8FAFC` background, bottom border 1px solid `#E2E8F0`, `label-sm` uppercase text in `#64748B`.
- Row cells: Top/bottom padding 12px, cell content in `numeric-table` with `font-feature-settings: "tnum" 1`. Hover row: `#F8FAFC` background transition. Selected row: `#EEF2FF` with 2px solid `#4F46E5` left-border accent.

### Checkboxes & Radios
- Checkboxes: 16px square, 3px corner radius, 1px solid `#CBD5E1`. Checked state: `#4F46E5` fill with pure white verification checkmark.
- Radio buttons: 16px circular, 1px solid `#CBD5E1`. Selected state: `#FFFFFF` core enclosed by a 5px solid `#4F46E5` ring.