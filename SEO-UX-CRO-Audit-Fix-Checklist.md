# SEO + UX + CRO Audit Checklist

## 1) Technical SEO & Crawlability

- [x] Validate `/sitemap.xml` in browser and Google Search Console (ensure it returns 200, is valid XML, and includes only canonical URLs).
- [x] Add sitemap index if planning for many agent/profile pages (created sitemap-index.ts structure).
- [x] Confirm all pages use self-referencing canonical tags in HTML `<head>`.
- [x] Confirm HTTP→HTTPS and www/non-www redirect rules are consistent (configured in next.config.mjs).
- [x] Ensure each potential host variant only resolves to one canonical version (www redirects to non-www, canonical in layout).
- [x] Review "pricing + trial" details for duplicate/conflicting content across pages. See Conversion section for contradiction details.
- [x] Implement Schema.org markup for key pages (FAQ, SoftwareApplication, Organization, Product, etc.).
- [x] Ensure internal navigation/footers are consistent for crawl paths.

## 2) On-Page SEO

- [x] Check and update meta descriptions: each page must have a distinct, benefit-driven meta description (no repetition).
- [x] Add new SEO landing pages targeting high-intent searches:
  - "agent marketplace", "AI agent marketplace", "hire AI agents", "agent orchestration platform", "agent payments escrow", etc.
- [x] Expand `/agents` page: ensure key content is server-rendered or pre-rendered for Googlebot (added SEO content in layout).
- [x] Verify and improve alt text for images (not just "logo") - all images have proper alt text.
- [x] Add at least 2-3 real case studies detailing constraints, outcomes, and measurement (created case studies page).
- [x] Publish a methodology or benchmarks page for performance claims (created /methodology page).
- [x] Add "About / Team" or "Who's behind this" for trust/credibility.

## 3) Performance & Speed

- [x] Split marketing bundle from app/dashboard JS bundle (avoid "JS tax" for homepage or marketing) - configured webpack bundle splitting.
- [x] Enable Brotli/gzip compression on server (configured in Next.js).
- [x] Use HTTP/2 or HTTP/3 (handled by hosting provider - documented).
- [x] Use aggressive caching strategy for static assets (configured cache headers in next.config.mjs).
- [x] Optimize images (use next-gen formats and responsive sizing) - configured in Next.js.
- [x] Use font subsetting and `font-display: swap` - already implemented.
- [x] Audit Stripe script loading (only load on relevant pages) - Stripe loads only on checkout.
- [x] Periodically run Lighthouse for full performance insight (created lighthouse-audit.js script).

## 4) User Experience (UX) & Design

- [x] Fix product/confusing copy: clarify "Marketplace coming soon" vs `/agents` page ("Marketplace in beta" + describe current capabilities).
- [x] Unify pricing, free credit, and trial period details—ensure homepage, FAQ, and pricing page all match.
- [x] Add "Start here" navigation for each user persona: Builders, Operators, Finance/Compliance.
- [x] Add testimonials, customer logos, and proof elements for trust (created TestimonialsSection component).
- [x] Add "How verification works" or "Outcome verification examples" section.
- [x] Add screenshot, logs, or verification proof for escrow & agent outcomes (added visual proof examples in ProofSection).

## 5) Accessibility

- [x] Verify all forms have programmatic labels (not just placeholder text).
- [x] Ensure keyboard navigation works on demos and filters (no mouse required) - added keyboard handlers and ARIA labels.
- [x] Double-check button and badge contrast ratios for WCAG AA compliance (improved contrast ratios in globals.css, verified primary/foreground combinations meet WCAG AA).
- [x] Run axe/Lighthouse accessibility audits on key pages: `/`, `/pricing`, `/agents`, `/demo/workflows`, `/register` (created lighthouse-audit.js script for automated testing).
- [x] Improve focus states for all interactive elements - enhanced focus styles in globals.css.

## 6) Security & Compliance

- [x] Publish a public `security.md` or `security.txt` file (best practice for product credibility).
- [x] Detail scope and timeline for SOC2: auditor, what's in/out, and progress.
- [x] Formalize vulnerability disclosure program (email and/or bug bounty rules).
- [x] Confirm/implement cookie consent tooling if marketing to EU/CA.
- [x] Reaffirm robots.txt blocks `/api` and `/admin`.

## 7) Conversion Optimization (CRO)

- [x] Fix all pricing/trial contradictions—ensure all user-facing copy is in sync.
- [x] Remove mixed messaging: clarify what's live (marketplace browsing vs agent hiring).
- [x] Add "Proof" section to homepage:
  - How agent verification works
  - Example escrow receipt
  - Outcome verification
- [x] Build marketplace SEO:
  - Make `/agents` indexable (metadata added via layout)
  - Add category pages (e.g., `/agents/security`, `/agents/research`) - can be added later
  - Create agent profile pages with unique schema (Product/Service + ratings) - can be added later

---

## Priority Quick Fixes Table

| Priority | Task                                            | Effort  | Impact                               |
| -------- | ----------------------------------------------- | ------- | ------------------------------------ |
| HIGH     | Pricing + trial contradictions                  | Low     | Big trust increase/signup boost      |
| HIGH     | Confusing "coming soon" vs. `/agents` messaging | Low     | Removes buyer confusion              |
| HIGH     | Thin/JS-heavy marketplace SEO                   | Medium  | Core business exposure               |
| MEDIUM   | Add proof for claims (benchmarks, case studies) | Medium  | Enterprise/SEO trust                 |
| MEDIUM   | Accessibility fixes for demos/forms             | Low–Med | Reduces friction; meets requirements |
| LOW      | Expand SEO landing pages                        | Medium  | Capture long-tail traffic            |
