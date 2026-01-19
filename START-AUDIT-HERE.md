# 🚀 START HERE - Audit Agent Instructions

## Welcome, Audit Agent!

You've been assigned to verify the Base44 dark theme redesign implementation. This is a comprehensive audit task.

## Your First Steps

1. **Read this file completely** ✅ (You're doing this now!)

2. **Read the main audit checklist:**

   ```
   Read: DESIGN-AUDIT-VERIFICATION.md
   ```

   This contains all 12 phases with specific verification steps.

3. **Read detailed instructions:**

   ```
   Read: AGENT-AUDIT-INSTRUCTIONS.md
   ```

   This has detailed patterns, commands, and procedures.

4. **Run the verification script:**

   ```powershell
   powershell -ExecutionPolicy Bypass -File verify-dark-theme-changes.ps1
   ```

   This will automatically check for common issues.

5. **Start verifying:**
   - Open `DESIGN-AUDIT-VERIFICATION.md`
   - Go through each phase systematically
   - Check off `[x]` items as you verify them
   - Document issues in `AUDIT-ISSUES.md`

## What Was Changed

The entire website was converted from a light theme to a dark theme:

- **Backgrounds:** Changed from white/light to pure black
- **Text:** Changed to white/slate colors
- **Colors:** Removed all yellow/brass colors
- **Logo:** Updated to new SwarmSync logo
- **Buttons:** Standardized to chrome/metallic styling
- **50+ files** were modified across the codebase

## Your Task

Verify that all changes were implemented correctly:

- ✅ All pages have dark backgrounds
- ✅ All text is readable (white/slate on black)
- ✅ No yellow/brass colors remain
- ✅ Logo appears correctly everywhere
- ✅ Buttons are consistent
- ✅ Components use dark theme

## Files You'll Work With

1. **`DESIGN-AUDIT-VERIFICATION.md`** - Main checklist (UPDATE THIS)
2. **`AUDIT-ISSUES.md`** - Issues you find (CREATE THIS)
3. **`VERIFICATION-REPORT.md`** - Auto-generated report (REVIEW THIS)
4. **`verify-dark-theme-changes.ps1`** - Verification script (RUN THIS)

## Verification Process

For each phase in the checklist:

1. **Read the verification steps**
2. **Check the files listed**
3. **Verify the patterns** (use grep/search)
4. **Check visually** (if page accessible)
5. **Mark as complete** `[x]`
6. **Document issues** if found

## Key Commands

```powershell
# Search for yellow colors
Get-ChildItem -Path apps\web\src -Recurse -Include *.tsx,*.ts,*.css | Select-String -Pattern "text-yellow"

# Search for brass colors
Get-ChildItem -Path apps\web\src -Recurse -Include *.tsx,*.ts,*.css | Select-String -Pattern "text-brass"

# Search for old color system
Get-ChildItem -Path apps\web\src -Recurse -Include *.tsx,*.ts | Select-String -Pattern "text-ink"

# Check if file exists
Test-Path "apps\web\src\app\page.tsx"

# Read file content
Get-Content "apps\web\src\app\page.tsx" | Select-String -Pattern "bg-black"
```

## Expected Outcomes

When you're done:

- ✅ All 12 phases verified
- ✅ No yellow/brass colors remaining (or documented)
- ✅ All pages have dark theme
- ✅ Logo appears correctly
- ✅ Buttons are consistent
- ✅ All text is readable

## Need Help?

- **Patterns to check:** See `AGENT-AUDIT-INSTRUCTIONS.md`
- **Detailed steps:** See `DESIGN-AUDIT-VERIFICATION.md`
- **Quick reference:** See `NEW-AGENT-AUDIT-TASK.md`

## Ready to Start?

1. ✅ Read `DESIGN-AUDIT-VERIFICATION.md`
2. ✅ Run `verify-dark-theme-changes.ps1`
3. ✅ Start with Phase 1
4. ✅ Work through all 12 phases
5. ✅ Create `AUDIT-ISSUES.md` with findings

**Let's begin!** 🎯
