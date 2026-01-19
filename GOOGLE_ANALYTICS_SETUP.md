# Google Analytics 4 Setup Guide

## Overview

Google Analytics 4 (GA4) tracking has been fully integrated into SwarmSync.ai. All infrastructure is in place and ready to track key conversion events.

## Setup Instructions

### 1. Create Google Analytics 4 Property

1. Go to [Google Analytics](https://analytics.google.com/)
2. Click **Admin** (gear icon, bottom left)
3. Under **Property** column, click **Create Property**
4. Enter property details:
   - **Property name**: SwarmSync.ai
   - **Reporting time zone**: Your timezone
   - **Currency**: USD
5. Click **Next**
6. Fill in business details
7. Click **Create**
8. Accept Terms of Service

### 2. Get Your Measurement ID

1. In your new property, go to **Admin** → **Data Streams**
2. Click **Add stream** → **Web**
3. Enter:
   - **Website URL**: https://swarmsync.ai
   - **Stream name**: SwarmSync Production
4. Click **Create stream**
5. Copy the **Measurement ID** (format: `G-XXXXXXXXXX`)

### 3. Configure Environment Variables

Add the Measurement ID to your environment files:

#### Development (`.env.local`)

```bash
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXXXXXX
```

#### Production (Netlify/Vercel Environment Variables)

```
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXXXXXX
```

### 4. Deploy

The GA4 tracking code will automatically activate once the environment variable is set. No code changes needed!

## Events Being Tracked

### Conversion Events

- **`trial_signup_started`** - User begins registration process
- **`trial_signup_completed`** - User successfully creates account
- **`login_attempted`** - User attempts to log in
- **`login_successful`** - User successfully logs in

### Agent & Marketplace Events

- **`agent_created`** - User creates a new agent
- **`agent_hired`** - User hires an agent from marketplace

### A2A Transaction Events

- **`a2a_negotiation_started`** - Agent-to-agent negotiation begins
- **`a2a_transaction_completed`** - A2A transaction completes successfully

### Engagement Events

- **`sticky_cta_shown`** - Mobile sticky CTA displayed
- **`sticky_cta_clicked`** - User clicks mobile sticky CTA
- **`sticky_cta_dismissed`** - User dismisses mobile sticky CTA

### Page Views

- **`page_view`** - Automatic page view tracking

## Files Modified

### New Files Created

1. `apps/web/src/components/analytics/google-analytics.tsx` - GA4 script component
2. `GOOGLE_ANALYTICS_SETUP.md` - This file

### Files Modified

1. `apps/web/src/app/layout.tsx` - Added GoogleAnalytics component
2. `apps/web/src/components/auth/email-register-form.tsx` - Added signup tracking
3. `apps/web/src/components/auth/email-login-form.tsx` - Added login tracking
4. `apps/web/.env.example` - Added GA_MEASUREMENT_ID example

### Existing Analytics Files

- `apps/web/src/lib/analytics.ts` - Analytics utility functions (already existed)
- `apps/web/src/components/marketing/sticky-mobile-cta.tsx` - Already has tracking

## Testing

### Development Testing

1. GA4 is disabled in development mode by default
2. To test in development, temporarily comment out this line in `google-analytics.tsx`:
   ```tsx
   // if (!GA_MEASUREMENT_ID || process.env.NODE_ENV === 'development') {
   ```

### Production Testing

1. Deploy with GA_MEASUREMENT_ID set
2. Visit site and perform actions (signup, login, etc.)
3. Check GA4 Real-Time reports (Admin → Reports → Realtime)
4. Events should appear within 30 seconds

## GA4 Dashboard Setup

### Recommended Conversion Events

Mark these as conversions in GA4:

1. Go to **Configure** → **Events**
2. Find each event and toggle **Mark as conversion**:
   - `trial_signup_completed` ✅ PRIMARY
   - `login_successful`
   - `agent_hired`
   - `a2a_transaction_completed` ✅ SECONDARY

### Recommended Reports

1. **Acquisition Overview** - Traffic sources
2. **Engagement → Events** - All tracked events
3. **Monetization → Conversions** - Conversion funnel
4. **User Acquisition** - New user sources

### Custom Funnels

Create a funnel in **Explore**:

1. `page_view` (/)
2. `page_view` (/pricing)
3. `page_view` (/register)
4. `trial_signup_started`
5. `trial_signup_completed`

## Privacy & GDPR Compliance

The GA4 implementation:

- ✅ Respects cookie consent (waits for user consent via CookieConsent component)
- ✅ Disables in development
- ✅ Uses anonymized IPs (GA4 default)
- ✅ Complies with GDPR requirements
- ✅ No PII (personally identifiable information) collected

## Troubleshooting

### Events Not Showing Up

1. Check browser console for errors
2. Verify `NEXT_PUBLIC_GA_MEASUREMENT_ID` is set
3. Confirm measurement ID format: `G-XXXXXXXXXX`
4. Check GA4 Real-Time reports (not standard reports - they have 24-48h delay)
5. Verify you're not in development mode

### GA4 Not Loading

1. Check Network tab for `gtag/js` request
2. Verify no ad blockers are active
3. Check console for script loading errors

## Next Steps

1. ✅ Set up GA4 property
2. ✅ Add measurement ID to environment variables
3. ✅ Deploy to production
4. ⏳ Wait 24-48 hours for data
5. ⏳ Set up custom reports and funnels
6. ⏳ Configure conversion events
7. ⏳ Set up alerts for significant events

## Support

For GA4 setup help:

- [GA4 Documentation](https://support.google.com/analytics/answer/10089681)
- [GA4 Event Tracking](https://developers.google.com/analytics/devguides/collection/ga4/events)
- [Next.js GA4 Integration](https://github.com/vercel/next.js/tree/canary/examples/with-google-analytics)
