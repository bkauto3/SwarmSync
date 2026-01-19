// Google Analytics 4 event tracking
declare global {
  interface Window {
    gtag?: (
      command: 'event' | 'config' | 'set',
      targetId: string,
      config?: Record<string, any>
    ) => void;
    dataLayer?: any[];
  }
}

export function trackEvent(
  eventName: string,
  eventParams?: {
    event_category?: string;
    event_label?: string;
    value?: number;
    [key: string]: any;
  }
) {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', eventName, eventParams);
  }
}

export function trackPageView(url: string) {
  trackEvent('page_view', {
    page_path: url,
  });
}

export function trackTrialSignupStarted() {
  trackEvent('trial_signup_started', {
    event_category: 'conversion',
    event_label: 'trial_signup',
  });
}

export function trackTrialSignupCompleted() {
  trackEvent('trial_signup_completed', {
    event_category: 'conversion',
    event_label: 'trial_signup',
  });
}

export function trackLoginAttempted() {
  trackEvent('login_attempted', {
    event_category: 'authentication',
  });
}

export function trackLoginSuccessful() {
  trackEvent('login_successful', {
    event_category: 'authentication',
  });
}

export function trackAgentCreated() {
  trackEvent('agent_created', {
    event_category: 'agent_management',
  });
}

export function trackAgentHired() {
  trackEvent('agent_hired', {
    event_category: 'marketplace',
  });
}

export function trackA2ANegotiationStarted() {
  trackEvent('a2a_negotiation_started', {
    event_category: 'a2a',
  });
}

export function trackA2ATransactionCompleted() {
  trackEvent('a2a_transaction_completed', {
    event_category: 'a2a',
  });
}

export function trackStickyCTAShown() {
  trackEvent('sticky_cta_shown', {
    event_category: 'engagement',
    event_label: 'mobile_sticky_cta',
  });
}

export function trackStickyCTAClicked() {
  trackEvent('sticky_cta_clicked', {
    event_category: 'engagement',
    event_label: 'mobile_sticky_cta',
  });
}

export function trackStickyCTADismissed() {
  trackEvent('sticky_cta_dismissed', {
    event_category: 'engagement',
    event_label: 'mobile_sticky_cta',
  });
}
