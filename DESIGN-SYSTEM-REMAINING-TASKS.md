# Design System Remaining Tasks

This document tracks all remaining tasks to fully implement the design system based on visual audit feedback.

## Background Strategy (Marketing vs. App Split)

### Marketing Pages (Hero, Marketing Content)

- [ ] **Add Vignette Overlay**: Implement `.hero::before` with `radial-gradient(circle at center, transparent 0%, rgba(6,7,18,0.8) 100%)` to focus center content
- [ ] **Verify Starfield Opacity**: Ensure marketing pages keep full opacity starfield/network backgrounds
- [ ] **Apply to All Marketing Pages**: Hero section, about, platform, use-cases, security, FAQ, case-studies, methodology, agent-marketplace, agent-escrow-payments, agent-orchestration-guide, vs/build-your-own

### App Pages (Dashboard, Console, Agents, Test Library)

- [ ] **Reduce Starfield Opacity**: Set `DepthFieldOrbs` opacity to `0.3` for app pages (dashboard, console, agents, test library)
- [ ] **Add Solid Overlay**: Implement `.app-page::before` with `rgba(6,7,18,0.6)` overlay
- [ ] **Reduce ChromeNetworkBackground Opacity**: Set opacity to `0.3` for app pages
- [ ] **Ensure Z-Index Layering**: Overlay at `z-index: 1`, content at `z-index: 2`
- [ ] **Apply App Page Classes**: Ensure all app pages have `.app-page` class (dashboard, console pages, agents, test library)
- [ ] **Optional Background Toggle**: Verify background toggle exists in user settings and works correctly

## Surface Layering and Shadows

### Card/Panel Styling

- [ ] **Verify Surface Colors**: Ensure cards use `var(--surface-base)` (#0B0E1C) not flat black (#0a0f1f)
- [ ] **Implement Surface Raised**: Use `var(--surface-raised)` (#111524) for nested/inner panels and hover states
- [ ] **Add Shadow Panel**: Apply `box-shadow: var(--shadow-panel)` (0 4px 12px rgba(0,0,0,0.2)) to all cards
- [ ] **Update Recent Activity Cards**: Ensure cards in dashboard have proper surface/shadow
- [ ] **Update Agent Cards**: Ensure agent cards in marketplace have proper surface/shadow
- [ ] **Update Test Library Cards**: Ensure test library cards have proper surface/shadow
- [ ] **Verify Card Lift**: Cards should feel like "lifted panels on a console" not flat dark fills

## Typography Implementation

### Font Imports

- [ ] **Verify Space Grotesk Import**: Ensure `@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&display=swap');` exists
- [ ] **Verify Inter Import**: Ensure `@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');` exists

### Headings (Space Grotesk)

- [ ] **H1 Styling**: All h1 elements should use `font-family: 'Space Grotesk'`, `font-size: 48px`, `font-weight: 700`, `line-height: 1.1`
- [ ] **H2 Styling**: All h2 elements should use `font-family: 'Space Grotesk'`, `font-size: 32px`, `font-weight: 700`, `line-height: 1.2`
- [ ] **H3 Styling**: All h3 elements should use `font-family: 'Space Grotesk'`, `font-size: 24px`, `font-weight: 600`, `line-height: 1.3`
- [ ] **Heading Letter Spacing**: Ensure `letter-spacing: 0.02em` (max) on all headings
- [ ] **Hero Headline**: "Ready to onboard autonomy?" and similar hero headlines should be Space Grotesk 48px/700/1.1
- [ ] **Replace Generic Fonts**: Replace all generic `system-ui`, `Arial`, or default sans-serif with Space Grotesk for headings

### Body/UI Text (Inter)

- [ ] **Body Text**: All paragraphs should use `font-family: 'Inter'`, `font-size: 16px`, `font-weight: 400`, `line-height: 1.5`
- [ ] **Label/Nav Text**: All labels and nav items should use `font-family: 'Inter'`, `font-size: 14px`, `font-weight: 500`, `line-height: 1.4`
- [ ] **Meta Text**: All metadata/timestamps should use `font-family: 'Inter'`, `font-size: 12px`, `font-weight: 400`, `line-height: 1.4`
- [ ] **Body Letter Spacing**: Ensure `letter-spacing: 0em` for body text
- [ ] **Console Sturdy Weights**: Nav/rows should use weight 500-600 for "console sturdy" feel
- [ ] **Replace Generic Fonts**: Replace all generic sans-serif with Inter for body/UI text

### Tabular Numerals

- [ ] **Apply to Prices**: All prices (e.g., "$3.60") should use `font-variant-numeric: tabular-nums`
- [ ] **Apply to Timestamps**: All timestamps should use `font-variant-numeric: tabular-nums`
- [ ] **Create Utility Class**: Ensure `.text-meta-numeric` class exists and is applied consistently

## Accent Usage and Polish

### Accent Restriction

- [ ] **Remove Violet from Defaults**: Remove violet from default nav text, metadata/timestamps, section labels, secondary text
- [ ] **Violet Only for States**: Ensure violet (`var(--accent-primary)`) only appears on:
  - Active nav items
  - Hover states
  - Focus rings
  - Primary CTAs
- [ ] **Fix Footer Links**: Remove violet from footer links (should be neutral)
- [ ] **Fix Timestamp Colors**: Remove violet-ish colors from timestamps/meta in dashboard

### Buttons

- [ ] **Remove Glow**: Remove all glow/blur effects from buttons (e.g., "Start Free Trial" button)
- [ ] **Clean Chrome Style**: Buttons should be clean chrome with no glow
- [ ] **Primary Button**: Use `var(--accent-primary)` background, white text, no glow
- [ ] **Hover State**: Use `opacity: 0.9` on hover, no glow

### Focus States

- [ ] **Add Focus Rings**: Apply `box-shadow: var(--shadow-focus)` (0 0 0 2px rgba(124,92,255,0.3)) to all focusable inputs
- [ ] **Focus Border Color**: Use `border-color: var(--border-hover)` on focus

### Borders

- [ ] **Hover Border Brightness**: Ensure borders use `var(--border-hover)` (rgba(180,190,255,0.18)) on hover
- [ ] **Base Border Color**: Use `var(--border-base)` (rgba(180,190,255,0.12)) for default borders

## Specific Screen Updates

### Hero Section (Homepage)

- [ ] **Add Vignette**: Implement `.hero::before` vignette overlay
- [ ] **Nav Colors**: Change nav links to neutral grays (violet only on active/hover)
- [ ] **Headline Typography**: Ensure headline uses Space Grotesk 48px/700/1.1
- [ ] **Subtext Typography**: Ensure subtext uses Inter 18px with `var(--text-secondary)` color (not dark gray)
- [ ] **Subtext Contrast**: Fix low contrast on subtext (should be readable)
- [ ] **Button Styling**: Remove glow from hero CTA buttons, use clean primary style

### Dashboard Page

- [ ] **Add Muted Overlay**: Implement `.app-page::before` overlay with `rgba(6,7,18,0.6)`
- [ ] **Reduce Starfield Opacity**: Set starfield opacity to 0.3
- [ ] **Sidebar Nav**: Ensure default nav items are neutral (violet only on active)
- [ ] **Card Shadows**: Ensure all cards have `var(--shadow-panel)` shadow
- [ ] **Card Surfaces**: Ensure cards use `var(--surface-base)` not flat black
- [ ] **Typography**: Headings should be Space Grotesk, labels should be Inter 14px/500
- [ ] **Section Gaps**: Ensure 24px gaps between sections (`space-y-6`)
- [ ] **Recent Activity Cards**: Update to use proper surface/shadow

### Test Library / Cards Grid

- [ ] **Add App Overlay**: Implement `.app-page` overlay to mute background
- [ ] **Reduce Starfield**: Set starfield opacity to 0.3
- [ ] **Grid Cards**: Use `var(--surface-base)` with `var(--border-base)` border and `var(--shadow-panel)` shadow
- [ ] **Card Typography**: Headings Space Grotesk 24px, labels Inter 14px neutral
- [ ] **Violet Tags**: Restrict violet to verified badges/hover only
- [ ] **Consistent Padding**: Ensure 24px padding/gaps throughout
- [ ] **Grid Layout**: Use `display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px;`

### Agents Discovery Page

- [ ] **Add App Overlay**: Implement `.app-page` overlay to mute background
- [ ] **Reduce Starfield**: Set starfield opacity to 0.3
- [ ] **Agent Cards**: Use proper surface/shadow (not flat black)
- [ ] **Card Typography**: Headings Space Grotesk, labels Inter
- [ ] **Button/Badge Accents**: Restrict violet to hover/active states only
- [ ] **Grid Layout**: Use proper grid specs with 24px gaps

## Grid Layouts

- [ ] **Agents Grid**: Implement `display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px;`
- [ ] **Test Library Grid**: Implement proper grid layout with 24px gaps
- [ ] **Card Grids**: Ensure all card grids use consistent 24px gaps

## Inputs

- [ ] **Input Styling**: Ensure inputs use `var(--surface-raised)` background
- [ ] **Input Border**: Use `var(--border-base)` for default, `var(--border-hover)` on focus
- [ ] **Input Focus**: Apply `var(--shadow-focus)` focus ring
- [ ] **Input Typography**: Use Inter 14px for input text

## Verification Checklist

- [ ] **Visual Audit**: Review all screens match design specs
- [ ] **Background Check**: Verify marketing pages have vignette, app pages have overlay
- [ ] **Surface Check**: Verify cards have proper surface colors and shadows
- [ ] **Typography Check**: Verify Space Grotesk for headings, Inter for body/UI
- [ ] **Accent Check**: Verify violet only on active/hover/focus/CTAs
- [ ] **Button Check**: Verify no glow on buttons
- [ ] **Focus Check**: Verify focus rings on all inputs
- [ ] **Grid Check**: Verify proper grid layouts with 24px gaps
- [ ] **Tabular Nums Check**: Verify prices/timestamps use tabular numerals

## Priority Order

1. **High Priority** (Core Visual Issues):
   - Background strategy (vignette/overlay)
   - Surface layering and shadows
   - Typography (2-font system)

2. **Medium Priority** (Polish):
   - Accent restriction
   - Button glow removal
   - Focus states

3. **Low Priority** (Refinements):
   - Grid layouts
   - Input styling
   - Tabular numerals
