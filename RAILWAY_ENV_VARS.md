# Railway Environment Variables Setup

**Railway API URL:** `https://swarmsync-api.up.railway.app`

Add these environment variables to your Railway `swarmsync-api` service:

## Required Variables

```
DATABASE_URL=postgresql://neondb_owner:npg_v0RtJymP2rcw@ep-cold-butterfly-aenonb7s.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require
NODE_ENV=production
PORT=4000
JWT_SECRET=KiDqSkFDkfIoDS79ExH9OwWNNsPJSlLq9SzZzMYdoo8=
WEB_URL=https://swarmsync.ai
CORS_ALLOWED_ORIGINS=https://swarmsync.ai,https://www.swarmsync.ai
```

## Optional Variables (if needed)

```
SHADOW_DATABASE_URL=postgresql://neondb_owner:npg_v0RtJymP2rcw@ep-cold-butterfly-aenonb7s.c-2.us-east-2.aws.neon.tech/neondb_shadow?sslmode=require
STRIPE_SECRET_KEY=<your-stripe-secret-key>
STRIPE_WEBHOOK_SECRET=<your-stripe-webhook-secret>
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=<your-stripe-publishable-key>
AP2_WEBHOOK_SECRET=<your-ap2-webhook-secret>
AP2_REQUIRE_AUTH=true
```

## Instructions

1. Go to Railway dashboard → swarmsync-api service → Variables tab
2. Click "Raw Editor" button
3. Paste the required variables above
4. Generate a secure JWT_SECRET (you can use: `openssl rand -base64 32`)
5. Add any optional variables you need
6. Save the variables
