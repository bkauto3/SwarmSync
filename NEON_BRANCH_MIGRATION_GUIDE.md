# How to Deploy Migration to a Separate Neon Branch

This guide shows you how to create a Neon branch and run the migration there, so your existing tables remain untouched.

## Option 1: Using Neon Console (Recommended - Easiest)

### Step 1: Create a Branch in Neon Console

1. Go to [Neon Console](https://console.neon.tech)
2. Select your project (the one with `ep-cold-butterfly-aenonb7s`)
3. Click on **"Branches"** in the left sidebar
4. Click **"Create branch"** button
5. Name it something like `agent-testing` or `swarm-sync-testing`
6. Choose to branch from your main branch (usually `main`)
7. Click **"Create branch"**

### Step 2: Get the Branch Connection String

1. After the branch is created, click on it
2. Go to the **"Connection Details"** tab
3. Copy the **Connection string** (it will look like):
   ```
   postgresql://neondb_owner:password@ep-xxxxx-xxxxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

### Step 3: Run Migration on the Branch

1. **Temporarily update your DATABASE_URL** (you can do this in a few ways):

   **Option A: Set it in the command line** (Windows PowerShell):

   ```powershell
   cd apps/api
   $env:DATABASE_URL="postgresql://neondb_owner:password@ep-xxxxx-xxxxx.us-east-2.aws.neon.tech/neondb?sslmode=require"
   npx prisma migrate deploy
   ```

   **Option B: Create a temporary .env file**:

   ```powershell
   cd apps/api
   # Create a backup of your current .env
   Copy-Item .env .env.backup
   # Edit .env and temporarily change DATABASE_URL to the branch connection string
   # Then run:
   npx prisma migrate deploy
   # Then restore your original .env
   Copy-Item .env.backup .env
   ```

   **Option C: Use a .env.testing file**:

   ```powershell
   cd apps/api
   # Create .env.testing with the branch DATABASE_URL
   # Then run:
   $env:DATABASE_URL=(Get-Content .env.testing | Select-String "DATABASE_URL").ToString().Split("=")[1]
   npx prisma migrate deploy
   ```

### Step 4: Verify Migration

After running the migration, you can verify it worked:

```powershell
cd apps/api
$env:DATABASE_URL="your-branch-connection-string"
npx prisma studio
```

This will open Prisma Studio where you can see the new `TestSuite` and `TestRun` tables.

### Step 5: Update Your App to Use the Branch (Optional)

If you want your app to use the branch:

1. Update your `.env` file (or production environment variables) with the branch connection string
2. Or keep using the main branch and merge later (see below)

## Option 2: Using Neon CLI (If You Have It)

If you have the Neon CLI installed:

```bash
# Install Neon CLI (if not installed)
npm install -g neonctl

# Login
neonctl auth

# Create branch
neonctl branches create --project-id your-project-id --name agent-testing

# Get connection string
neonctl connection-string --project-id your-project-id --branch-name agent-testing

# Then use that connection string in Step 3 above
```

## Option 3: Merge Branch Later (If You Want)

Once you've tested everything on the branch and it works:

1. In Neon Console, go to your branch
2. Click **"Merge"** or **"Promote to main"** (if available)
3. This will merge all the new tables into your main database
4. Your existing tables will remain untouched

## Important Notes

- **Branches are isolated**: Changes on a branch don't affect your main database
- **Branches cost money**: Neon charges for branch storage, but it's usually minimal
- **You can delete branches**: If you don't need it anymore, you can delete it in the console
- **Connection strings are different**: Each branch has its own connection string

## Quick Command Reference

```powershell
# Set branch DATABASE_URL and run migration
cd apps/api
$env:DATABASE_URL="postgresql://neondb_owner:password@ep-xxxxx-xxxxx.us-east-2.aws.neon.tech/neondb?sslmode=require"
npx prisma migrate deploy

# Verify tables were created
npx prisma studio
```

## Troubleshooting

**"Connection refused"**: Make sure you copied the entire connection string including `?sslmode=require`

**"Migration already applied"**: The migration was already run. Check Prisma Studio to see if tables exist.

**"Table already exists"**: You might be connected to the wrong branch. Double-check your connection string.
