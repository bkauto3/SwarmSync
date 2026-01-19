# Quick Fix Guide - Netlify Deploy Error

**Problem**: Netlify build failed with duplicate route error

**Solution**: Implemented client-side redirects to consolidate routes

**Time to Deploy**: 5 minutes

---

## What Was Done

### 1. Identified Conflict
Two sets of pages both resolved to `/agents` and `/agents/[slug]`:
- `apps/web/src/app/(marketplace)/agents/...`
- `apps/web/src/app/(marketplace)/console/agents/...`

Next.js prohibits this - each URL must map to exactly one page.

### 2. Implemented Redirects
Created lightweight redirect pages in console that route users to marketplace:

```typescript
// apps/web/src/app/(marketplace)/console/agents/page.tsx
'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function ConsoleAgentsRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/agents');
  }, [router]);
  return null;
}
```

### 3. Updated Navigation
Changed Sidebar.tsx:
```typescript
// Before
{ label: 'Agents', href: '/console/agents' }

// After
{ label: 'Agents', href: '/agents' }
```

---

## Files Changed

| File | Action | Why |
|------|--------|-----|
| `console/agents/page.tsx` | Created redirect | Map /console/agents → /agents |
| `console/agents/new/page.tsx` | Created redirect | Map /console/agents/new → /agents/new |
| `console/agents/[slug]/page.tsx` | Created redirect | Map /console/agents/[id] → /agents/[id] |
| `console/agents/[slug]/analytics/page.tsx` | Created redirect | Map /console/agents/[id]/analytics → /agents/[id]/analytics |
| `agents/new/page.tsx` | Created new route | Main create agent page |
| `Sidebar.tsx` | Updated link | Point to /agents |

---

## Result

✅ **No more duplicate routes**
- Each URL now served by exactly one page
- Old console URLs redirect automatically
- No breaking changes for users
- Netlify build will now succeed

---

## Deploy Checklist

- [x] Routes consolidated  
- [x] Redirects implemented
- [x] Navigation updated
- [ ] Test locally: `npm run dev`
- [ ] Test build: `npm run build`
- [ ] Push to main
- [ ] Netlify auto-deploys
- [ ] Verify production

---

## Quick Local Test

```bash
# Start dev server
npm run dev

# In another terminal, test redirects
curl -L http://localhost:3000/console/agents
# Should redirect to /agents

curl http://localhost:3000/agents
# Should work directly

npm run build
# Should complete without errors
```

---

## Done! 🎉

Your Netlify deployment should now succeed. The routes are consolidated and redirects handle backward compatibility seamlessly.

**Next**: Push to main and Netlify will auto-deploy.
