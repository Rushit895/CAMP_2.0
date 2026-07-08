---
name: Technical Precision
colors:
  surface: '#0b1324'
  surface-dim: '#0b1324'
  surface-bright: '#31394b'
  surface-container-lowest: '#060e1e'
  surface-container-low: '#131b2c'
  surface-container: '#171f30'
  surface-container-high: '#222a3b'
  surface-container-highest: '#2d3547'
  on-surface: '#dae2fa'
  on-surface-variant: '#c7c4d8'
  inverse-surface: '#dae2fa'
  inverse-on-surface: '#283042'
  outline: '#918fa1'
  outline-variant: '#464555'
  surface-tint: '#c3c0ff'
  primary: '#c3c0ff'
  on-primary: '#1d00a5'
  primary-container: '#4f46e5'
  on-primary-container: '#dad7ff'
  inverse-primary: '#4d44e3'
  secondary: '#d0bcff'
  on-secondary: '#3c0091'
  secondary-container: '#571bc1'
  on-secondary-container: '#c4abff'
  tertiary: '#4cd7f6'
  on-tertiary: '#003640'
  tertiary-container: '#006a7c'
  on-tertiary-container: '#93e8ff'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e2dfff'
  primary-fixed-dim: '#c3c0ff'
  on-primary-fixed: '#0f0069'
  on-primary-fixed-variant: '#3323cc'
  secondary-fixed: '#e9ddff'
  secondary-fixed-dim: '#d0bcff'
  on-secondary-fixed: '#23005c'
  on-secondary-fixed-variant: '#5516be'
  tertiary-fixed: '#acedff'
  tertiary-fixed-dim: '#4cd7f6'
  on-tertiary-fixed: '#001f26'
  on-tertiary-fixed-variant: '#004e5c'
  background: '#0b1324'
  on-background: '#dae2fa'
  surface-variant: '#2d3547'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  body-base:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: '0'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: '0'
  label-mono:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0.02em
  data-tabular:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  container-max: 1280px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

This design system is engineered for high-performance SaaS environments, drawing inspiration from industry leaders in developer tools and technical documentation. The aesthetic is rooted in **Modern Minimalism** with a **Technical** edge, emphasizing clarity, determinism, and professional rigor.

The brand personality is authoritative yet unobtrusive. It utilizes generous whitespace to reduce cognitive load while employing precise geometric elements to convey a sense of reliability. Visual interest is generated through subtle gradients and micro-interactions rather than decorative flourishes. The emotional response should be one of quiet confidence—the feeling of using a tool that is as stable as it is sophisticated.

## Colors

The palette is anchored by a deep Indigo primary accent, signaling intelligence and stability. The system defaults to **Dark Mode** to align with technical professional preferences, though it maintains a high-contrast Light Mode for accessibility and documentation.

- **Primary Accent (#4F46E5):** Used for primary actions, active states, and key brand highlights.
- **Secondary Accent (Violet):** Used for supplementary data visualization and progressive disclosure elements.
- **Functional Gradients:** Subtle linear gradients (Indigo to Violet) may be used for premium surfaces or "hero" states to add depth without breaking the minimal aesthetic.
- **Surface Logic:** Backgrounds are slightly tinted (not pure black or white) to reduce eye strain and provide a softer canvas for high-contrast text.

## Typography

The typography system relies on **Inter** for its exceptional legibility and neutral, systematic feel. It is paired with **Geist** for technical labels and tabular data to reinforce the "developer-first" aesthetic.

- **Scale:** High contrast between headlines and body text to establish clear hierarchy.
- **Technical Elements:** Use the `label-mono` role for tags, code snippets, and metadata.
- **Tabular Numerals:** All data-heavy matrices and numeric displays must use `data-tabular` settings to ensure vertical alignment across columns.
- **Tracking:** Tightened letter spacing on larger headlines (-0.02em) creates a more "locked-in" and professional display.

## Layout & Spacing

The layout utilizes a **12-column fluid grid** with a fixed maximum width for content-heavy pages to maintain readability. 

- **Grid Logic:** Use 24px gutters for desktop and 16px for mobile.
- **Spacing Rhythm:** An 8pt linear scale is the foundation for all layout decisions (4px, 8px, 16px, 24px, 32px, 48px, 64px).
- **Whitespace:** Emphasize "macro-whitespace" between major sections (64px+) to allow the technical content to breathe. Use "micro-whitespace" (8px-12px) within components like cards and list items to maintain density where precision is required.

## Elevation & Depth

This system uses **Tonal Layering** combined with **Low-contrast Outlines** to create depth. Avoid heavy, muddy shadows.

- **Surfaces:** In dark mode, use slightly lighter hex values for elevated surfaces (e.g., Background #0E1118 -> Card #161B22).
- **Borders:** Every card and menu should have a 1px solid border. In dark mode, use `rgba(255, 255, 255, 0.08)`. In light mode, use `rgba(0, 0, 0, 0.05)`.
- **Shadows:** Use "Ambient Shadows"—extremely soft, multi-layered shadows with a high blur-to-spread ratio. Shadows should feel like a subtle glow rather than a physical drop shadow.
- **Transitions:** All elevation changes (e.g., hovering over a card) must use a 200ms `cubic-bezier(0.4, 0, 0.2, 1)` easing.

## Shapes

The design system employs a consistent **14px corner radius** for all primary containers and cards. This specific radius provides a modern, balanced look that is neither too sharp nor too "bubbly."

- **Cards:** Fixed 14px radius.
- **Buttons:** 8px radius (Small/Medium) or 14px (Large) to match cards.
- **Inputs:** 8px radius to ensure they sit comfortably inside larger 14px containers.
- **Strictness:** Do not use full-pill shapes unless for specific status badges or tags.

## Components

### Buttons
Primary buttons use the Indigo accent with white text. Hover states should feature a subtle brightness increase or a very soft Indigo glow. Use `geist` for button text to maintain the technical feel.

### Cards
Cards are the primary structural unit. They must feature the 14px radius, a 1px subtle border, and a soft ambient shadow on hover. Backgrounds should be one step lighter/darker than the main page background.

### Inputs & Fields
Use a "ghost" style: transparent background with a 1px border. On focus, the border transitions to Indigo and gains a 2px outer glow (ring) with 20% opacity.

### Chips & Badges
Small, low-contrast pills with `label-mono` typography. Use them for status (e.g., "Active", "Beta", "v2.0.4").

### Navigation
Top navigation should be semi-transparent with a `backdrop-filter: blur(12px)` to create a glassmorphism effect as the user scrolls, maintaining the sense of depth and technical layering.

### Lists & Data Grids
Rows should have a subtle hover highlight (`rgba(primary, 0.05)`). Use the `data-tabular` font setting for all numeric columns to ensure perfect vertical alignment of decimal points and digits.