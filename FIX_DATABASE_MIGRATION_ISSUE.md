# 🚨 URGENT: Fix Database Migration Issue

**Problem**: Prisma schema has fields that don't exist in database, causing all agent queries to fail

---

## 🎯 ROOT CAUSE

The Prisma schema (`apps/api/prisma/schema.prisma`) has these fields in the `Agent` model:

```prisma
recentSuccessRate Float?         // Line 105
reviewScore      Float?          // Line 106
reviewCount      Int @default(0) // Line 107
ratingConfidence Float?          // Line 108
```

But the **database migration was never run**, so these columns don't exist in the actual Neon database.

When Prisma tries to query agents, it fails with:

```
The column `Agent.recentSuccessRate` does not exist in the current database.
```

---

## ✅ SOLUTION 1: Remove Fields from Schema (FASTEST - 2 minutes)

Since these fields aren't being used yet (they're for the improved rating formula), we can just remove them from the schema.

### **Step 1: Remove Fields from Schema**

Edit `apps/api/prisma/schema.prisma` and remove lines 105-108:

```prisma
model Agent {
  // ... existing fields ...
  trustScore      Int              @default(50)
  successCount    Int              @default(0)
  failureCount    Int              @default(0)
  // ❌ REMOVE THESE 4 LINES:
  // recentSuccessRate Float?
  // reviewScore      Float?
  // reviewCount      Int             @default(0)
  // ratingConfidence Float?
  lastExecutedAt  DateTime?
  basePriceCents  Int?
  // ... rest of fields ...
}
```

### **Step 2: Regenerate Prisma Client**

```powershell
cd apps/api
npx prisma generate
```

### **Step 3: Commit and Push**

```powershell
git add apps/api/prisma/schema.prisma
git commit -m "Fix: Remove unused rating fields from schema (not migrated)"
git push origin main
```

### **Step 4: Wait for Railway to Redeploy**

Railway will auto-redeploy (~2 minutes)

### **Step 5: Test**

```powershell
Invoke-WebRequest -Uri "https://swarmsync-api.up.railway.app/agents" | Select-Object -ExpandProperty Content | ConvertFrom-Json
```

Should return agents successfully!

---

## ✅ SOLUTION 2: Run Migration (PROPER - 10 minutes)

If you want to keep these fields for future use, run the migration.

### **Step 1: Create Migration**

```powershell
cd apps/api
npx prisma migrate dev --name add_rating_fields
```

This will:

1. Create a new migration file
2. Apply it to your local database
3. Update Prisma client

### **Step 2: Apply Migration to Production (Neon)**

The migration needs to be applied to your Neon database. You have 2 options:

**Option A: Via Railway (Automatic)**

```powershell
# Commit the migration
git add apps/api/prisma/migrations
git commit -m "Add rating fields migration"
git push origin main
```

Railway will run migrations automatically on deploy.

**Option B: Manually via Prisma**

```powershell
# Set DATABASE_URL to Neon
$env:DATABASE_URL="postgresql://neondb_owner:npg_v0RtJymP2rcw@ep-bold-sun-ae1ajiqu-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"

# Run migration
npx prisma migrate deploy
```

### **Step 3: Test**

```powershell
Invoke-WebRequest -Uri "https://swarmsync-api.up.railway.app/agents" | Select-Object -ExpandProperty Content | ConvertFrom-Json
```

---

## 🎯 RECOMMENDED APPROACH

**Use Solution 1** (Remove fields) because:

- ✅ Fastest fix (2 minutes)
- ✅ No migration needed
- ✅ Fields aren't being used yet
- ✅ Can add them back later when implementing improved rating formula

**When to use Solution 2**:

- When you're ready to implement the improved rating formula
- When you have time to test migrations properly
- When you want to keep the schema in sync

---

## 📋 QUICK FIX SCRIPT

Here's a PowerShell script to do Solution 1 automatically:

```powershell
# Navigate to API directory
cd apps/api

# Remove the problematic lines from schema
$schemaPath = "prisma/schema.prisma"
$content = Get-Content $schemaPath -Raw

# Remove the 4 rating fields
$content = $content -replace '  recentSuccessRate Float\?\s+// Recent performance \(last 30 days\)\r?\n', ''
$content = $content -replace '  reviewScore\s+Float\?\s+// Average user review score \(1-5\)\r?\n', ''
$content = $content -replace '  reviewCount\s+Int\s+@default\(0\)\r?\n', ''
$content = $content -replace '  ratingConfidence\s+Float\?\s+// Confidence level \(0-1\)\r?\n', ''

# Save the file
$content | Set-Content $schemaPath -NoNewline

# Regenerate Prisma client
npx prisma generate

# Commit and push
git add prisma/schema.prisma
git commit -m "Fix: Remove unused rating fields from schema"
git push origin main

Write-Host "✅ Schema fixed! Railway will redeploy in ~2 minutes"
```

---

## 🧪 VERIFICATION

After fix is deployed:

### **Test 1: Agents Endpoint**

```powershell
Invoke-WebRequest -Uri "https://swarmsync-api.up.railway.app/agents" | Select-Object -ExpandProperty Content | ConvertFrom-Json
```

**Expected**: Returns array of agents (no error)

### **Test 2: Frontend Agents Page**

Visit: https://swarmsync.ai/agents
**Expected**: Agents display correctly

### **Test 3: Login**

Visit: https://swarmsync.ai/login
**Expected**: Login works

---

## 🔍 WHY THIS HAPPENED

1. The `IMPROVED_RATING_FORMULA.md` documentation suggested adding these fields
2. Someone added them to the Prisma schema
3. But forgot to run `npx prisma migrate dev`
4. The schema and database got out of sync
5. Prisma tries to SELECT columns that don't exist
6. All agent queries fail

---

## 🎯 NEXT STEPS

1. **Immediate**: Remove fields from schema (Solution 1)
2. **After fix**: Test agents page and login
3. **Later**: When implementing improved rating formula:
   - Add fields back to schema
   - Create proper migration
   - Test thoroughly before deploying

---

**Estimated Time**: 2 minutes (Solution 1) or 10 minutes (Solution 2)

**Impact**: HIGH - Fixes agents page and login

---

**Run Solution 1 now to get the site working again!** 🚀
