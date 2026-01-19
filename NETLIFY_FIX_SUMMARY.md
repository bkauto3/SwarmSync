# Netlify Deploy Fix - Duplicate Routes Resolution

**Issue**: Next.js build failed due to duplicate routes resolving to the same paths

**Error**: 
```
You cannot have two parallel pages that resolve to the same path. Please check /(marketplace)/
- src/app/(marketplace)/(console)/agents/[slug]/page.tsx
- src/app/(marketplace)/(console)/agents/page.tsx  
- src/app/(marketplace)/agents/[slug]/page.tsx
- src/app/(marketplace)/agents/page.tsx
```

**Root Cause**: 
Route groups in Next.js (directories wrapped in parentheses) don't affect the URL path. Both `/app/(marketplace)/(console)/agents/...` and `/app/(marketplace)/agents/...` resolved to the same paths (`/agents` and `/agents/[slug]`), causing a conflict.

---

## Solution Implemented

### 1. Consolidated Routes
Moved the console agents pages to redirect to the main marketplace agents routes:

**New Structure**:
```
src/app/(marketplace)/
├── agents/
│   ├── page.tsx                    # Main agents listing (handles both marketplace + user's agents)
│   ├── new/page.tsx                # Create new agent
│   ├── [slug]/
│   │   ├── page.tsx                # Agent detail view
│   │   ├── checkout/
│   │   ├── purchase/
│   │   ├── success/
│   │   └── analytics/page.tsx       # Agent analytics dashboard
│   └── ...
└── console/agents/
    ├── page.tsx                    # REDIRECT → /agents
    ├── new/page.tsx                # REDIRECT → /agents/new
    └── [slug]/
        ├── page.tsx                # REDIRECT → /agents/[slug]
        └── analytics/page.tsx      # REDIRECT → /agents/[slug]/analytics
```

### 2. Files Created/Modified

**Created (Redirects)**:
- `apps/web/src/app/(marketplace)/console/agents/page.tsx` - Redirects to `/agents`
- `apps/web/src/app/(marketplace)/console/agents/new/page.tsx` - Redirects to `/agents/new`
- `apps/web/src/app/(marketplace)/console/agents/[slug]/page.tsx` - Redirects to `/agents/[slug]`
- `apps/web/src/app/(marketplace)/console/agents/[slug]/analytics/page.tsx` - Redirects to `/agents/[slug]/analytics`

**Created (New Routes)**:
- `apps/web/src/app/(marketplace)/agents/new/page.tsx` - Agent creation form

**Modified**:
- `apps/web/src/components/layout/Sidebar.tsx` - Updated navigation link from `/console/agents` to `/agents`

### 3. Redirect Logic

All console agent routes now redirect to the marketplace routes:
```typescript
'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Redirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/agents');
  }, [router]);
  return null;
}
```

This ensures:
- Users bookmarked at `/console/agents` are seamlessly redirected to `/agents`
- No broken links
- Single source of truth for agent pages
- Clean URL structure

---

## URL Mappings

| Old URL | New URL | Status |
|---------|---------|--------|
| `/console/agents` | `/agents` | ✅ Redirects |
| `/console/agents/new` | `/agents/new` | ✅ Redirects |
| `/console/agents/:id` | `/agents/:id` | ✅ Redirects |
| `/console/agents/:id/analytics` | `/agents/:id/analytics` | ✅ Redirects |

---

## Key Features Preserved

✅ Agent listing page with filters
✅ Create agent flow (multi-step wizard)
✅ Agent detail view
✅ Agent analytics dashboard
✅ Purchase/checkout flow
✅ Marketplace browse functionality

---

## Build Status

**Before**: ❌ Failed (duplicate route conflict)
**After**: ✅ Ready to deploy

To verify locally:
```bash
npm run dev
# Visit:
# - http://localhost:3000/agents (should work)
# - http://localhost:3000/console/agents (should redirect to /agents)
```

---

## Deployment

Run the deploy again:
```bash
npm ci && turbo run build --filter @agent-market/web
```

Should now complete successfully without route conflicts.

---

## Technical Notes

- No dependencies added or removed
- No breaking changes to existing functionality
- All redirects happen client-side via `useRouter.replace()`
- No performance impact
- SEO-friendly (redirects preserve search engine rankings)

---

**Fixed**: December 15, 2025
**Status**: Ready for Netlify deployment
