# SwarmSync Recommendations Checklist

This checklist is derived from the **Website Build Analysis Report** (2026-01-19).

## 🔴 High Priority (Immediate Action)

- [ ] **Disable Production Source Maps**: Change `productionBrowserSourceMaps` to `false` in `next.config.mjs` to prevent source code exposure.
- [ ] **Add Error Tracking**: Install and configure Sentry (`@sentry/nextjs`) for production bug visibility.
- [ ] **Implement Error Boundaries**: Create `app/error.tsx` to handle runtime failures gracefully across the app.

## 🟡 Medium Priority (Next Sprint)

- [ ] **Add Bundle Analysis**: Install `@next/bundle-analyzer` to monitor and optimize bundle sizes.
- [ ] **Consolidate Logo Assets**: Audit and reduce the 10+ logo variations in `/public/logos/`.
- [ ] **Implement Content Security Policy (CSP)**: Add strict CSP headers in `next.config.mjs` to protect against XSS.
- [ ] **Expand Test Coverage**:
  - [ ] Install `@testing-library/react` and `@testing-library/jest-dom`.
  - [ ] Implement component tests (currently missing).
  - [ ] Aim for 60%+ coverage.

## 🟢 Low Priority (Backlog)

- [ ] **Component Refactoring**: Split components exceeding 150 lines (e.g., `agents/page.tsx`) into smaller, composable units.
- [ ] **Add Loading States**: Implement `loading.tsx` for all routes to improve perceived performance.
- [ ] **Lighthouse CI Integration**: Add `@lhci/cli` to the CI pipeline to detect performance regressions.

## 🛠️ Architectural & Code Quality Improvements

- [ ] **Custom Hooks**: Extract complex filtering and business logic from pages into custom hooks.
- [ ] **SSG Optimization**: Review data fetching logic in static pages to address the 120s generation timeout.
- [ ] **Suspense Boundaries**: Consistently implement Suspense boundaries for async components.
- [ ] **Documentation**: Add inline documentation for complex logic and components.

## ♿ Accessibility & SEO

- [ ] **Image Alt Text**: Verify all images have descriptive `alt` attributes.
- [ ] **Keyboard Navigation**: Conduct a full audit of keyboard navigation for all interactive elements.
- [ ] **Accessibility Audit**: Run a formal Lighthouse accessibility audit and fix reported issues.

## 📈 DevOps & Monitoring

- [ ] **Uptime Monitoring**: Set up a service like BetterStack or Pingdom.
- [ ] **Log Aggregation**: Implement log aggregation (e.g., Datadog, LogRocket).
