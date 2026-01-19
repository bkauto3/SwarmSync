# Design System Implementation Task Checklist

This document tracks the completion of all design system fixes based on the audit mismatches.

## Background Strategy

- [x] **Marketing Pages Vignette**: Ensure `.hero::before` vignette overlay is visible and working with radial gradient `rgba(6, 7, 18, 0.8)`
- [x] **App Pages Overlay**: Verify `.app-page::before` overlay with `rgba(6, 7, 18, 0.6)` is rendering correctly
- [x] **Starfield Opacity**: Ensure `DepthFieldOrbs` opacity is reduced to 0.3 for app pages
- [x] **Z-Index Layering**: Check overlay z-1, content z-2 is correct
- [x] **ChromeNetworkBackground Opacity**: Add conditional opacity (0.3 for app pages, 1.0 for marketing)

## Surface Layering and Shadows

- [x] **Replace glass-card**: Update all 47+ components using `glass-card` to use `.card` class with `var(--surface-base)` and `var(--shadow-panel)`
- [x] **Update Inner Panels**: Replace `bg-white/5` with `var(--surface-raised)` for nested panels
- [x] **Card Shadows**: Ensure all cards have `box-shadow: var(--shadow-panel)` applied
- [x] **Sidebar Background**: Update sidebar to use `var(--surface-base)` instead of `bg-surface`
- [x] **Sidebar Border**: Add `border-right: 1px solid var(--border-base)` to sidebar

## Accent Usage Restriction

- [x] **Navigation Accents**: Ensure violet (`var(--accent-primary)`) only appears on active nav items, hover states, focus rings, and primary CTAs
- [x] **Remove Violet from Defaults**: Remove violet from default nav text, metadata/timestamps, section labels, and secondary text
- [x] **Component Accent Audit**: Search and replace `text-accent`, `text-purple`, `text-violet`, `#7C5CFF` with appropriate neutral colors for non-active elements

## Typography Implementation

- [x] **Headings (Space Grotesk)**: Ensure all h1-h3 use `font-family: 'Space Grotesk'` with correct sizes (h1=48px/700, h2=32px/700, h3=24px/600)
- [x] **Heading Letter Spacing**: Verify `letter-spacing: 0.02em` (max) on all headings
- [x] **Body/UI Text (Inter)**: Ensure paragraphs, labels, nav use `font-family: 'Inter'` with correct sizes (body=16px/400, label/nav=14px/500)
- [x] **Body Letter Spacing**: Check `letter-spacing: 0em` for body text
- [x] **Meta Text**: Apply `font-variant-numeric: tabular-nums` to prices and timestamps
- [x] **Meta Text Color**: Use `var(--text-muted)` for meta text (12px/400)
- [x] **Component Typography**: Replace generic `font-body`, `font-headline` with explicit Space Grotesk/Inter in all components
- [x] **Text Colors**: Update all text colors to use design tokens (`var(--text-primary)`, `var(--text-secondary)`, `var(--text-muted)`)

## Borders and Focus States

- [x] **Border Colors**: Replace all `border-white/10` with `border: 1px solid var(--border-base)`
- [x] **Hover Borders**: Add hover state `border-color: var(--border-hover)` to interactive elements
- [x] **Focus Rings**: Apply `box-shadow: var(--shadow-focus)` to all focusable inputs
- [x] **Focus Border Color**: Ensure focus uses `border-color: var(--border-hover)`
- [x] **Border Radius Consistency**: Ensure all cards/buttons/inputs use `border-radius: 12px` (not 3xl/2xl)

## Specific Screen Updates

### Dashboard Page

- [x] **Dashboard Class**: Verify `.dashboard` class is applied
- [x] **Section Gaps**: Ensure 24px gaps between sections (`space-y-6` = 24px)
- [x] **Sidebar Styling**: Check sidebar uses `var(--surface-base)`
- [x] **Card Shadows**: Verify cards have shadows

### Hero Section

- [x] **Vignette Overlay**: Verify vignette overlay is visible
- [x] **Nav Colors**: Check nav uses neutral colors (violet only on active)
- [x] **Headline Typography**: Verify headline uses Space Grotesk 48px
- [x] **Subtext Typography**: Check subtext uses Inter 18px

### Live Demo Page

- [x] **Demo Feed Class**: Verify `.demo-feed` and `.step-card` classes applied
- [x] **Step Cards**: Check step cards use `var(--surface-raised)` with shadows
- [x] **Step Spacing**: Verify 32px spacing between steps
- [x] **Timestamps**: Check timestamps use tabular-nums

### Test Library Page

- [x] **Library Grid**: Verify `.library-grid` and `.library-card` classes applied
- [x] **Card Tokens**: Check cards use design tokens
- [x] **Grid Gaps**: Verify 24px gaps

## Component-Specific Updates

- [x] **Dashboard Components**: Update all components in `apps/web/src/components/dashboard/` (replace glass-card, update typography, apply tokens, add shadows)
- [x] **Quality Components**: Update all components in `apps/web/src/components/quality/` (same updates)
- [x] **Testing Components**: Update all components in `apps/web/src/components/testing/` (same updates)
- [x] **Agent Cards**: Update agent card components
- [x] **Workflow Components**: Update workflow components
- [x] **Billing Components**: Update billing components
- [x] **Analytics Components**: Update analytics components

## Optional Background Toggle

- [x] **User Settings Toggle**: Add toggle for "Remove background" option in settings
- [x] **Preference Storage**: Store preference in localStorage or user settings
- [x] **No Background Class**: Apply `.no-background` class when enabled
- [x] **CSS for Toggle**: Add `.no-background .depth-orbs { display: none; }` and `.no-background .chrome-network { display: none; }`

## Verification

- [x] **Visual Audit**: Check each screen matches design specs
- [x] **Accent Audit**: Verify no violet accents on non-active elements
- [x] **Typography Audit**: Confirm typography is correct throughout
- [x] **Shadow Audit**: Ensure shadows provide proper depth
- [x] **CSS Variable Audit**: Search for hardcoded colors that should use variables
- [x] **Token Usage**: Ensure all components use design tokens
- [x] **Old Token Removal**: Verify no old color system tokens remain
- [x] **Hardcoded Color Removal**: Replace remaining `text-white`, `text-black`, `text-slate-400`, etc. with design tokens
- [x] **Badge Colors**: Update badge components to use `var(--text-primary)` instead of `text-white`
- [x] **Inline Style Removal**: Replace all `style={{ fontVariantNumeric: 'tabular-nums' }}` with `text-meta-numeric` class
- [x] **Chart Gradient Colors**: Update chart gradients to use `var(--accent-primary)` instead of `slate-400`
