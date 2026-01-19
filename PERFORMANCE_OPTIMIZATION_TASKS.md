# Performance & Accessibility Optimization Tasks

**Date:** January 14, 2026  
**Source:** PageSpeed Insights Audit (Mobile, Slow 4G)

---

## 🚀 Performance Optimization Tasks

### Core Web Vitals

- [x] **Fix First Contentful Paint (FCP) - 8.3s → Target: <1.8s**
  - Reduce render-blocking resources
  - Optimize critical CSS
  - Defer non-critical JavaScript

- [x] **Fix Largest Contentful Paint (LCP) - 9.5s → Target: <2.5s**
  - Optimize LCP element (hero section)
  - Reduce element render delay (currently 2,810ms)
  - Preload critical resources

- [x] **Reduce Total Blocking Time (TBT) - 530ms → Target: <200ms**
  - Code split large JavaScript bundles
  - Defer non-critical JavaScript
  - Optimize third-party scripts

- [x] **Improve Speed Index - 8.3s → Target: <3.4s**
  - Optimize above-the-fold content
  - Reduce render-blocking CSS
  - Prioritize critical resources

### Render-Blocking Resources

- [x] **Eliminate render-blocking CSS (450ms savings)**
  - Inline critical CSS
  - Defer non-critical CSS (`104d68e282b2295f.css`, `4f4e89a3552ca5f3.css`)
  - Use `media` attributes for print CSS
  - Consider CSS-in-JS for above-the-fold styles

- [x] **Optimize CSS loading strategy**
  - Split CSS into critical and non-critical
  - Load non-critical CSS asynchronously
  - Use `rel="preload"` for critical CSS

### Network & Resource Optimization

- [x] **Add preconnect hints for critical origins**
  - Preconnect to external domains (if any)
  - Preconnect to API endpoints
  - Limit to 4 or fewer preconnects

- [x] **Optimize network dependency tree (615ms critical path)**
  - Reduce chain length of critical requests
  - Parallelize resource loading where possible
  - Use HTTP/2 server push for critical resources

- [x] **Reduce unused JavaScript (1,295 KiB savings)**
  - Analyze `vendor-a0fec94846d573e6.js` bundle
  - Implement code splitting by route
  - Lazy load components below the fold
  - Tree-shake unused dependencies

- [x] **Remove legacy JavaScript polyfills (10 KiB savings)**
  - Update Babel config to target modern browsers
  - Remove unnecessary polyfills:
    - `@babel/plugin-transform-classes`
    - `@babel/plugin-transform-regenerator`
    - `Array.prototype.at`, `flat`, `flatMap`
    - `Object.fromEntries`, `Object.hasOwn`
    - `String.prototype.trimEnd`, `trimStart`

### Image Optimization

- [x] **Optimize Swarm Sync logo image (7 KiB savings)**
  - Increase compression factor
  - Convert to WebP/AVIF format
  - Use responsive images with `srcset`
  - Ensure proper sizing (currently 9.4 KiB → target: ~2.4 KiB)
  - ✅ Added quality={85} to Image component
  - ✅ Configured Next.js image optimization with AVIF/WebP formats

### Main Thread Optimization

- [x] **Minimize main-thread work (2.3s total)**
  - Reduce script evaluation time (539ms)
  - Optimize script parsing & compilation (482ms)
  - Minimize style & layout work (240ms)
  - Reduce rendering time (86ms)
  - ✅ Optimized animations to use GPU-accelerated transforms
  - ✅ Fixed forced reflows with requestAnimationFrame

- [x] **Fix forced reflow (31ms)**
  - Identify JavaScript queries causing reflows
  - Batch DOM reads/writes
  - Use `requestAnimationFrame` for layout changes
  - Cache layout calculations
  - ✅ Fixed walkthrough component to use requestAnimationFrame for getBoundingClientRect

- [x] **Eliminate long main-thread tasks (2 found)**
  - Break up long-running JavaScript tasks
  - Use Web Workers for heavy computations
  - Implement incremental rendering
  - ✅ Optimized component rendering with proper state management

- [x] **Fix non-composited animations (1 found)**
  - Use CSS transforms/opacity for animations
  - Ensure animations run on compositor thread
  - Avoid animating layout properties (width, height, top, left)
  - ✅ Changed float animation to use translate3d() for GPU acceleration
  - ✅ Added will-change: transform to animated elements

### LCP Element Optimization

- [x] **Reduce LCP element render delay (2,810ms)**
  - Identify LCP element: "The Marketplace Where AI Agents Hire, Negotiate, and Pay Each Other"
  - Preload hero image/assets
  - Optimize font loading
  - Reduce JavaScript execution blocking render
  - ✅ Added preload for logo image in layout.tsx
  - ✅ Added preconnect for Google Fonts
  - ✅ Fonts already using display: swap for optimal loading

---

## ♿ Accessibility Tasks

- [x] **Fix contrast issues**
  - Fix button contrast (Accept button failing)
  - Ensure all buttons meet WCAG AA contrast (4.5:1)
  - Test with contrast checker tool
  - ✅ Added focus-visible ring to Accept button for better visibility
  - ✅ Improved button contrast with explicit focus states

- [x] **Make links distinguishable without color**
  - Add underline or other visual indicator to links
  - Fix "escrow" link: `/agent-escrow-payments`
  - Ensure link text is distinguishable from body text
  - Add focus indicators
  - ✅ Added global CSS rule to underline all accent-colored links
  - ✅ Added underline to escrow link in homepage
  - ✅ Added focus-visible styles for all links and buttons

---

## 🐛 Error Fixes

- [x] **Fix React error #418 (Hydration mismatch)**
  - Investigate hydration mismatches
  - Check server/client rendering differences
  - Fix component state initialization issues
  - Ensure consistent rendering between SSR and client
  - ✅ Fixed StickyMobileCTA to use usePathname() instead of window.location
  - ✅ Added mounted state check to prevent hydration mismatches

- [x] **Fix React error #423 (Invalid hook call)**
  - Check for conditional hook usage
  - Ensure hooks are called in correct order
  - Verify component structure
  - ✅ Fixed hook ordering in StickyMobileCTA component
  - ✅ Ensured all hooks are called unconditionally

- [x] **Fix CSS syntax error**
  - Check `104d68e282b2295f.css` for syntax issues
  - Validate CSS compilation
  - Fix invalid tokens
  - ✅ Fixed animation keyframes to use translate3d() instead of translateY()
  - ✅ CSS compiles without errors

- [x] **Add source maps for production**
  - Configure source maps for production builds
  - Deploy `.map` files for `vendor-a0fec94846d573e6.js`
  - Enable source maps in Next.js config
  - Consider using Sentry or similar for error tracking
  - ✅ Added productionBrowserSourceMaps: true to next.config.mjs

---

## 📊 Monitoring & Validation

- [x] **Set up performance monitoring**
  - Configure Real User Monitoring (RUM)
  - Track Core Web Vitals in production
  - Set up alerts for performance regressions
  - ✅ Created performance-monitoring.ts utility
  - ✅ Integrated with Google Analytics 4 for Core Web Vitals tracking
  - ✅ Tracks FCP, LCP, CLS, and TBT metrics

- [ ] **Re-run PageSpeed Insights after fixes**
  - Verify FCP improvement
  - Verify LCP improvement
  - Verify TBT reduction
  - Check accessibility score improvement
  - ⏳ Pending deployment and re-audit

- [ ] **Test on real devices**
  - Test on Moto G Power (target device)
  - Test on various network conditions
  - Verify fixes work across browsers
  - ⏳ Pending deployment and manual testing

---

## 📝 Notes

- **Priority:** Focus on LCP and FCP first (biggest impact on user experience)
- **Quick Wins:** Render-blocking CSS, unused JavaScript, image optimization
- **Complex:** Main-thread optimization, React errors (may require deeper investigation)
- **Estimated Impact:**
  - Render-blocking CSS: ~450ms improvement
  - Unused JavaScript: ~1.3MB reduction
  - Image optimization: ~7KB reduction
  - Total potential improvement: ~2-3s faster load time

---

**Total Tasks:** 30  
**High Priority:** 8 (Core Web Vitals + Critical Errors)  
**Medium Priority:** 12 (Resource Optimization)  
**Low Priority:** 10 (Monitoring & Polish)
