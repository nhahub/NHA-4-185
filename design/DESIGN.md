---
name: FraudShield Narrative
colors:
  surface: '#051424'
  surface-dim: '#051424'
  surface-bright: '#2c3a4c'
  surface-container-lowest: '#010f1f'
  surface-container-low: '#0d1c2d'
  surface-container: '#122131'
  surface-container-high: '#1c2b3c'
  surface-container-highest: '#273647'
  on-surface: '#d4e4fa'
  on-surface-variant: '#c5c6cd'
  inverse-surface: '#d4e4fa'
  inverse-on-surface: '#233143'
  outline: '#8f9097'
  outline-variant: '#44474d'
  surface-tint: '#b9c7e4'
  primary: '#b9c7e4'
  on-primary: '#233148'
  primary-container: '#0a192f'
  on-primary-container: '#74829d'
  inverse-primary: '#515f78'
  secondary: '#b3c5ff'
  on-secondary: '#002b75'
  secondary-container: '#0266ff'
  on-secondary-container: '#f9f7ff'
  tertiary: '#00dbe7'
  on-tertiary: '#00363a'
  tertiary-container: '#001d1f'
  on-tertiary-container: '#009098'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d6e3ff'
  primary-fixed-dim: '#b9c7e4'
  on-primary-fixed: '#0d1c32'
  on-primary-fixed-variant: '#39475f'
  secondary-fixed: '#dae1ff'
  secondary-fixed-dim: '#b3c5ff'
  on-secondary-fixed: '#001849'
  on-secondary-fixed-variant: '#003fa4'
  tertiary-fixed: '#74f5ff'
  tertiary-fixed-dim: '#00dbe7'
  on-tertiary-fixed: '#002022'
  on-tertiary-fixed-variant: '#004f54'
  background: '#051424'
  on-background: '#d4e4fa'
  surface-variant: '#273647'
typography:
  headline-xl:
    fontFamily: Manrope
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  data-mono:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-padding: 32px
  gutter: 24px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

The design system is engineered to evoke a sense of **unshakable security** and **predictive intelligence**. It targets high-stakes decision-makers in banking and fintech who require clarity amidst complex data streams.

The aesthetic follows a **High-End Corporate Minimalism** approach mixed with **Futuristic Precision**. It avoids unnecessary ornamentation, favoring structural integrity, expansive whitespace, and purposeful movement. The interface should feel like a sophisticated command center—calm under pressure, yet technologically advanced.

**Key Visual Principles:**
- **Intelligence:** Data is prioritized through clear hierarchy and monochromatic foundations.
- **Protection:** Solid blocks of deep navy provide a literal "shield" of visual weight.
- **Precision:** Thin lines and geometric alignment suggest mathematical accuracy.

## Colors

The palette is anchored in a "Deep Space" dark mode to reduce eye strain during long monitoring sessions and to emphasize the glowing AI accents.

- **Primary (Deep Navy):** Used for structural surfaces, sidebars, and primary backgrounds to establish authority.
- **Secondary (Electric Blue):** Used for primary actions and active states, signifying "the machine at work."
- **Accent (Cyan):** Reserved for AI-driven insights, data pings, and highlight metrics.
- **Success (Emerald):** Used strictly for "Cleared" or "Safe" status indicators.
- **Neutral:** A range of cool grays that recede into the background, ensuring content remains the focus.

## Typography

This design system utilizes a multi-font strategy to balance human-centric readability with technical precision.

- **Manrope (Headlines):** Its modern, geometric curves provide a premium feel for titles and key metrics.
- **Inter (Body):** Chosen for its exceptional legibility in data-heavy enterprise tables and descriptions.
- **Geist (Data/Labels):** A monospaced-leaning sans used for transaction IDs, timestamps, and small uppercase labels to reinforce the "developer-grade" AI aesthetic.

**Scale Usage:**
- Use **Headline XL** for dashboard hero metrics only.
- Use **Label Caps** for section headers above cards to create a clear "system" look.
- Use **Data Mono** for all numerical values and identifiers to ensure character alignment.

## Layout & Spacing

The layout philosophy is based on a **Fixed-Fluid Hybrid Grid**. 
- **Desktop:** 12-column grid with a fixed-width sidebar (280px) and a fluid content area.
- **Rhythm:** A strict 4px baseline grid ensures all elements align vertically.
- **Whitespace:** Emphasize generous margins (32px+) around primary data visualizations to prevent cognitive overload.

**Breakpoints:**
- **Desktop (1440px+):** Full 12-column display.
- **Tablet (768px - 1439px):** Content collapses to 8 columns; sidebar becomes a collapsed icon-only rail.
- **Mobile (< 767px):** Single-column stack; horizontal scrolling enabled for data tables.

## Elevation & Depth

In this design system, depth is communicated through **Tonal Layering** rather than traditional shadows. This maintains a clean, modern aesthetic.

- **Level 0 (Background):** The darkest hex (#020617), used for the canvas.
- **Level 1 (Cards/Panels):** Deep Navy (#0A192F) with a subtle 1px border (#1E293B). 
- **Level 2 (Modals/Popovers):** Slightly lighter navy with a subtle Cyan-tinted outer glow (0px 4px 20px rgba(0, 242, 255, 0.05)) to suggest it is "active" and "intelligent."

**Borders:** Use thin, low-contrast lines (1px) for internal dividers to keep the UI crisp and light despite the dark palette.

## Shapes

The shape language is **Soft yet Structured**. By using a subtle `0.25rem` radius (Soft), the UI feels approachable but retains the "hard edges" associated with enterprise security and military-grade software.

- **Interactive Elements:** Buttons and inputs use a consistent 4px (Soft) radius.
- **Containers:** Dashboard cards use 8px (Large) to create a distinct grouping of information.
- **Visual Cues:** Status "pips" or AI pulse indicators should be perfectly circular to contrast against the rectangular grid.

## Components

### Buttons
- **Primary:** Solid Electric Blue with white text. No gradient, flat design.
- **Secondary:** Transparent with a 1px Cyan border. On hover, a subtle 10% Cyan fill.
- **Ghost:** Text-only in Neutral gray, turning White on hover.

### Cards
Cards are the primary container. They must feature a 1px border (#1E293B). Titles should be in **Label Caps** to differentiate from the data within.

### Input Fields
Inputs use a dark background (#020617) with a subtle 1px border. On focus, the border transitions to Electric Blue with a sharp, non-blurred 2px focus ring.

### Data Visualizations
- **Lines:** Use a 2px stroke width. Primary data in Cyan, secondary in Electric Blue.
- **Gradients:** Only used for area charts, transitioning from 30% opacity Cyan to 0% at the baseline.
- **Points:** High-risk data points should "pulse" using a subtle scale animation.

### Chips/Badges
Small, pill-shaped indicators.
- **High Risk:** Deep Red background with light red text.
- **Safe:** Emerald green background (low opacity) with solid emerald text.
- **Processing:** Neutral gray with a "loading" shimmer effect.