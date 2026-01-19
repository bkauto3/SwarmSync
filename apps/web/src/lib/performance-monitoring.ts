// Performance monitoring utilities for Core Web Vitals and custom metrics

export interface WebVitalsMetric {
  id: string;
  name: string;
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  delta: number;
  entries: PerformanceEntry[];
}

const allowedRatings = ['good', 'needs-improvement', 'poor'] as const;
type AllowedRating = (typeof allowedRatings)[number];

const normalizeRating = (rating: string | undefined): AllowedRating => {
  return allowedRatings.includes(rating as AllowedRating)
    ? (rating as AllowedRating)
    : 'needs-improvement';
};

export function reportWebVitals(metric: WebVitalsMetric) {
  // Send to Google Analytics 4
  if (typeof window !== 'undefined' && (window as any).gtag) {
    (window as any).gtag('event', metric.name, {
      event_category: 'Web Vitals',
      value: Math.round(metric.value),
      event_label: metric.id,
      non_interaction: true,
    });
  }

  // Log to console in development
  if (process.env.NODE_ENV === 'development') {
    console.log(`[Web Vitals] ${metric.name}:`, {
      value: metric.value,
      rating: metric.rating,
      id: metric.id,
    });
  }
}

export function measurePerformance() {
  if (typeof window === 'undefined' || !('PerformanceObserver' in window)) {
    return;
  }

  // Measure FCP (First Contentful Paint)
  try {
    const fcpObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.name === 'first-contentful-paint') {
          const metric = {
            id: entry.entryType,
            name: 'FCP',
            value: entry.startTime,
            rating: normalizeRating(
              entry.startTime < 1800
                ? 'good'
                : entry.startTime < 3000
                  ? 'needs-improvement'
                  : 'poor',
            ),
            delta: entry.startTime,
            entries: [entry],
          };
          reportWebVitals(metric);
        }
      }
    });
    fcpObserver.observe({ entryTypes: ['paint'] });
  } catch (e) {
    // PerformanceObserver not supported
  }

  // Measure LCP (Largest Contentful Paint)
  try {
    const lcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const lastEntry = entries[entries.length - 1] as any;
      if (lastEntry) {
        const metric = {
          id: lastEntry.id || 'lcp',
          name: 'LCP',
          value: lastEntry.renderTime || lastEntry.loadTime,
          rating: normalizeRating(
            lastEntry.renderTime < 2500
              ? 'good'
              : lastEntry.renderTime < 4000
                ? 'needs-improvement'
                : 'poor',
          ),
          delta: lastEntry.renderTime || lastEntry.loadTime,
          entries: [lastEntry],
        };
        reportWebVitals(metric);
      }
    });
    lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
  } catch (e) {
    // PerformanceObserver not supported
  }

  // Measure CLS (Cumulative Layout Shift)
  try {
    let clsValue = 0;
    const clsObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries() as any[]) {
        if (!entry.hadRecentInput) {
          clsValue += entry.value;
        }
      }
      const metric = {
        id: 'cls',
        name: 'CLS',
        value: clsValue,
        rating: normalizeRating(
          clsValue < 0.1
            ? 'good'
            : clsValue < 0.25
              ? 'needs-improvement'
              : 'poor',
        ),
        delta: clsValue,
        entries: [],
      };
      reportWebVitals(metric);
    });
    clsObserver.observe({ entryTypes: ['layout-shift'] });
  } catch (e) {
    // PerformanceObserver not supported
  }

  // Measure TBT (Total Blocking Time) approximation
  try {
    const longTaskObserver = new PerformanceObserver((list) => {
      let totalBlockingTime = 0;
      for (const entry of list.getEntries() as any[]) {
        if (entry.duration > 50) {
          totalBlockingTime += entry.duration - 50;
        }
      }
      if (totalBlockingTime > 0) {
        const metric = {
          id: 'tbt',
          name: 'TBT',
          value: totalBlockingTime,
          rating: normalizeRating(
            totalBlockingTime < 200
              ? 'good'
              : totalBlockingTime < 600
                ? 'needs-improvement'
                : 'poor',
          ),
          delta: totalBlockingTime,
          entries: [],
        };
        reportWebVitals(metric);
      }
    });
    longTaskObserver.observe({ entryTypes: ['longtask'] });
  } catch (e) {
    // Long Task API not supported
  }
}

// Initialize performance monitoring on page load
if (typeof window !== 'undefined') {
  if (document.readyState === 'complete') {
    measurePerformance();
  } else {
    window.addEventListener('load', measurePerformance);
  }
}
