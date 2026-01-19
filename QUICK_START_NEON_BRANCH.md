# Quick Start: Deploy to Neon Branch

## Step-by-Step (5 minutes)

### 1. Create Branch in Neon Console

1. Go to https://console.neon.tech
2. Click your project
3. Click **"Branches"** → **"Create branch"**
4. Name it: `agent-testing`
5. Click **"Create"**

### 2. Copy Branch Connection String

1. Click on your new branch
2. Go to **"Connection Details"**
3. Click **"Copy"** next to the connection string
4. It looks like: `postgresql://neondb_owner:password@ep-xxxxx-xxxxx.us-east-2.aws.neon.tech/neondb?sslmode=require`

### 3. Run Migration

**Option A: Use the PowerShell script** (easiest):

```powershell
cd apps/api
.\run-migration-on-branch.ps1 "paste-your-branch-connection-string-here"
```

**Option B: Manual command**:

```powershell
cd apps/api
$env:DATABASE_URL="paste-your-branch-connection-string-here"
npx prisma migrate deploy
```

### 4. Verify It Worked

```powershell
npx prisma studio
```

You should see `TestSuite` and `TestRun` tables in the list.

### 5. Update Your App (Optional)

If you want your app to use the branch, update your `.env` file:

```env
DATABASE_URL=your-branch-connection-string-here
```

## That's It! 🎉

Your migration is now on a separate branch. Your existing tables are safe.

## Need Help?

See `NEON_BRANCH_MIGRATION_GUIDE.md` for detailed instructions and troubleshooting.
