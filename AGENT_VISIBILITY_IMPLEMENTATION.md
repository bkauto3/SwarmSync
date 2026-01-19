# Agent Visibility Feature Implementation

## Summary

Implemented agent visibility settings allowing users to control who can see and use their agents with three visibility levels: PUBLIC, PRIVATE, and ORGANIZATION.

## Changes Made

### 1. Database Schema (`apps/api/prisma/schema.prisma`)

- Added `ORGANIZATION` to the `AgentVisibility` enum
- Enum now supports: `PUBLIC`, `PRIVATE`, `UNLISTED`, `ORGANIZATION`

### 2. Migration

- Created migration file: `apps/api/prisma/migrations/20251214_add_organization_visibility/migration.sql`
- Adds `ORGANIZATION` value to the enum using `ALTER TYPE`

### 3. Backend API (`apps/api/src/modules/agents/`)

#### `agents.service.ts`

- Updated `findAll()` method to accept `userId` and `organizationId` parameters
- Implemented visibility filtering logic:
  - **Unauthenticated users**: Only see PUBLIC agents
  - **Authenticated users**: See PUBLIC + their own PRIVATE agents + ORGANIZATION agents (if in org)
  - **Creators**: Always see their own agents regardless of visibility

#### `agents.controller.ts`

- Added `@CurrentUser()` decorator to `findAll()` endpoint
- Passes `userId` and `organizationId` to service for visibility filtering

#### `guards/jwt-auth.guard.ts`

- Modified to optionally authenticate on public routes
- Populates `request.user` if valid credentials provided, even on public endpoints
- Allows unauthenticated access to public routes while still capturing user context

### 4. Frontend UI (`apps/web/src/app/(marketplace)/(console)/agents/new/page.tsx`)

- Updated `Visibility` type to include `'ORGANIZATION'`
- Enhanced visibility selector with three options:
  - **Public (everyone can use)**: Visible in marketplace to all users
  - **Organization (team only)**: Only visible to org members
  - **Private (just me)**: Only visible to creator
- Added descriptive help text for each visibility option

## How It Works

### Agent Discovery Flow

1. User browses marketplace (`GET /agents`)
2. Backend checks if user is authenticated
3. Applies visibility filter:
   ```typescript
   if (authenticated) {
     return PUBLIC agents
       OR (PRIVATE agents where creator = user)
       OR (ORGANIZATION agents where org = user.org)
   } else {
     return PUBLIC agents only
   }
   ```

### Agent Creation Flow

1. User selects visibility during agent creation
2. Visibility is stored in `Agent.visibility` field
3. Agent is only discoverable according to visibility rules

## Next Steps

### Required Actions

1. **Generate Prisma Client**: Run `npx prisma generate` in `apps/api` to update TypeScript types
2. **Run Migration**: Run `npx prisma migrate deploy` to apply database changes
3. **Restart API Server**: The dev server should auto-restart, but manual restart may be needed

### Testing

- Create agents with different visibility settings
- Test discovery as:
  - Unauthenticated user (should only see PUBLIC)
  - Authenticated user (should see PUBLIC + own PRIVATE)
  - Organization member (should see PUBLIC + own PRIVATE + org's ORGANIZATION agents)

### Future Enhancements

- Add visibility filter to agent edit page
- Add organization selector for ORGANIZATION visibility
- Add visibility badge on agent cards
- Add analytics for visibility-based discovery

## Files Modified

- `apps/api/prisma/schema.prisma`
- `apps/api/src/modules/agents/agents.service.ts`
- `apps/api/src/modules/agents/agents.controller.ts`
- `apps/api/src/modules/auth/guards/jwt-auth.guard.ts`
- `apps/web/src/app/(marketplace)/(console)/agents/new/page.tsx`

## Files Created

- `apps/api/prisma/migrations/20251214_add_organization_visibility/migration.sql`
