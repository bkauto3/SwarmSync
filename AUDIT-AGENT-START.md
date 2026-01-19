# 🚀 START HERE - Agent Audit Instructions

## Your Task

You are an audit agent tasked with verifying the Base44 dark theme redesign implementation. Your goal is to systematically go through `DESIGN-AUDIT-VERIFICATION.md` and verify each item.

## Quick Start

1. **Read the audit document:**

   ```
   Read: DESIGN-AUDIT-VERIFICATION.md
   ```

2. **Run the verification script:**

   ```
   Run: verify-dark-theme-changes.ps1
   ```

3. **Review the instructions:**

   ```
   Read: AGENT-AUDIT-INSTRUCTIONS.md
   ```

4. **Start verifying:**
   - Go through each phase in `DESIGN-AUDIT-VERIFICATION.md`
   - Check off items as you verify them
   - Document any issues in `AUDIT-ISSUES.md`

## Verification Order

1. **Phase 1: Logo Replacement** - Check logo file and references
2. **Phase 2: Remove Yellow/Brass Colors** - Search codebase for remaining colors
3. **Phase 3: Demo Pages** - Verify demo pages have dark theme
4. **Phase 4: Checkout Buttons** - Verify button styling consistency
5. **Phase 5: Login & Register** - Verify auth pages
6. **Phase 6: Agents Page** - Verify marketplace page
7. **Phase 7: Console Pages** - Verify dashboard pages
8. **Phase 8: Marketing Pages** - Verify all marketing pages
9. **Phase 9: UI Components** - Verify component library
10. **Phase 10: Footer & Global** - Verify footer and global styles
11. **Phase 11: Agent Detail** - Verify agent detail pages
12. **Phase 12: Testing** - Final verification

## Key Commands

### Search for color violations:

```powershell
# Find yellow colors
grep -r "text-yellow" apps/web/src

# Find brass colors
grep -r "text-brass" apps/web/src

# Find old color system
grep -r "text-ink" apps/web/src
```

### Verify files exist:

```powershell
Test-Path "apps/web/src/app/page.tsx"
Test-Path "apps/web/public/swarm-sync-logo.png"
```

### Check file contents:

```powershell
Get-Content "apps/web/src/app/page.tsx" | Select-String "bg-black"
```

## Expected Outcomes

- ✅ All phases verified
- ✅ No yellow/brass colors remaining
- ✅ All pages have dark theme
- ✅ Logo appears correctly
- ✅ Buttons are consistent
- ✅ All text is readable

## Reporting

Create `AUDIT-ISSUES.md` with any problems found:

```markdown
# Audit Issues

## Issue #1: [Description]

- **Phase:** Phase X
- **File:** path/to/file.tsx
- **Line:** 123
- **Issue:** [Description]
- **Fix:** [Suggested fix]
```

## Completion

When done:

1. All items in `DESIGN-AUDIT-VERIFICATION.md` should be checked `[x]`
2. `AUDIT-ISSUES.md` should be created (even if empty)
3. `VERIFICATION-REPORT.md` should be reviewed
4. Summary report created

Good luck! 🎯
